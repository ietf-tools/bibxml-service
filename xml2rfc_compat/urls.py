"""Implements a registry of xml2rfc-style path resolver (fetcher) functions
and provides utilities for constructing patterns
fit for inclusion in site’s root URL configuration."""

import logging
import functools
import re
from typing import Callable, List, Union, Dict, Tuple, TypedDict, cast

from django.urls import re_path
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from django.http import HttpResponse, JsonResponse

from pydantic import ValidationError

from prometheus import metrics
from bib_models.models import BibliographicItem
from sources.exceptions import RefNotFoundError
from main.query import build_citation_for_docid

from .aliases import unalias, get_aliases
from .models import Xml2rfcItem, dir_subpath_regex, ManualPathMap
from .serializer import to_xml_string


log = logging.getLogger(__name__)


fetcher_registry: Dict[str, Callable[[str], BibliographicItem]] = {}
"""Maps xml2rfc subdirectory name to a function
that returns a bibliographic item."""


def get_urls():
    """Returns a list of URL patterns suitable for inclusion
    in site’s root URL configuration.

    Fetcher functions should have been all registered prior
    to calling this function.
    """

    return [
        pattern
        for dirname, fetcher_func in fetcher_registry.items()
        for pattern in make_xml2rfc_path_pattern(
            [dirname, *get_aliases(dirname)],
            fetcher_func)
    ]
    return fetcher_registry.values()


def register_fetcher(dirname: str):
    """Parametrized decorator that returns a registering function
    for resolver/fetcher function for given ``dirname``.

    Fetcher function is passed the ``anchor`` kwarg,
    for which it must return a :class:`BibliographicData` instance,
    and is expected to raise either ``RefNotFoundError``
    or pydantic’s ``ValidationError``.
    """
    def register(fetcher_func: Callable[[str], BibliographicItem]):
        fetcher_registry[dirname] = fetcher_func
        return fetcher_func
    return register


def make_xml2rfc_path_pattern(
        dirnames: List[str],
        fetcher_func: Callable[[str], BibliographicItem]):
    """Constructs Django URL resolver patterns
    for a given list of dirnames.

    Each path is in the shape of
    ``<dirname>/[_]reference.<anchor>.xml``,
    and constructed view delegates bibliographic item
    retrieval to provided fetcher function.
    """
    return [
        re_path(
            dir_subpath_regex % dirname,
            never_cache(require_safe(
                _make_xml2rfc_path_handler(fetcher_func),
            )),
            name='xml2rfc_%s' % dirname)
        for dirname in dirnames
    ]


def resolve_manual_map(subpath: str) -> Tuple[
    Union[str, None],
    Union[BibliographicItem, None],
    Union[str, None],
]:
    """Returns a 3-tuple of mapping configuration, resolved item,
    and error as a string, any can be None.
    Does not raise exceptions.
    """
    mapped_docid: Union[str, None]
    resolved_item: Union[BibliographicItem, None]
    error: Union[str, None]
    try:
        manual_map = ManualPathMap.objects.get(xml2rfc_subpath=subpath)
    except ManualPathMap.DoesNotExist:
        mapped_docid = None
        resolved_item = None
        error = "not found"
    else:
        mapped_docid = manual_map.docid
        try:
            resolved_item = build_citation_for_docid(cast(str, mapped_docid))
        except ValidationError:
            log.exception(
                "Unable to validate item manually mapped to xml2rfc path %s "
                "via docid %s",
                subpath,
                mapped_docid)
            error = "validation problem"
            resolved_item = None
        except RefNotFoundError:
            log.exception(
                "Unable to resolve an item for xml2rfc path %s, "
                "despite it being manually mapped via docid %s",
                subpath,
                mapped_docid)
            error = "not found"
            resolved_item = None
        else:
            error = None

    return mapped_docid, resolved_item, error


def resolve_automatically(
    subpath: str,
    anchor: str,
    fetcher_func: Callable[[str], BibliographicItem],
) -> Tuple[
    str,
    Union[BibliographicItem, None],
    Union[str, None],
]:
    """Returns a 3-tuple of resolver function name, resolved item,
    and error as a string, any can be None.
    Does not raise exceptions.
    """
    item: Union[BibliographicItem, None]
    error: Union[str, None]
    try:
        item = fetcher_func(anchor)
    except RefNotFoundError:
        log.exception(
            "Unable to resolve xml2rfc path automatically: %s",
            subpath)
        error = "not found"
        item = None
    except ValidationError:
        log.exception(
            "Item found for xml2rfc path did not validate: %s",
            subpath)
        error = "validation problem"
        item = None
    else:
        error = None

    return fetcher_func.__name__, item, error


class ResolutionOutcome(TypedDict, total=True):
    config: str
    error: str


def _make_xml2rfc_path_handler(fetcher_func: Callable[
    [str], BibliographicItem
]):
    """Creates a view function, given a fetcher function.

    Fetcher function will only be called if manual map was not found
    or did not resolve successfully.

    Fetcher function will receive full requested subpath
    (not including the unchanging prefix)
    and a cleaned xml2rfc filename
    (just the anchor, without the “reference.” or “_reference.” prefix
    or the .xml extension),
    and must return a :class:`BibliographicItem` instance.

    The automatically created view function handles filename
    cleanup, constructing a :class:`BibliographicItem`
    and serializing it into an XML string with proper anchor tag supplied.
    """

    @functools.wraps(fetcher_func)
    def handle_xml2rfc_path(request, xml2rfc_subpath: str, anchor: str):
        resp: HttpResponse
        item: Union[BibliographicItem, None]
        xml_repr: Union[str, None]

        methods = ["manual", "auto", "fallback"]
        method_results: Dict[str, ResolutionOutcome] = {}

        mapped_docid, item, error = resolve_manual_map(xml2rfc_subpath)
        if mapped_docid:
            method_results['manual'] = dict(
                config=mapped_docid,
                error='' if item else (error or "no error information"),
            )

        if not item:
            func_name, item, error = resolve_automatically(
                xml2rfc_subpath,
                anchor,
                fetcher_func)
            method_results['auto'] = dict(
                config=func_name,
                error='' if item else (error or "no error information"),
            )

        if item:
            xml_repr = to_xml_string(item, anchor=anchor)
        else:
            xml_repr = _obtain_fallback_xml(
                xml2rfc_subpath,
                anchor)
            method_results['fallback'] = dict(
                config='',
                error='' if xml_repr else "not indexed",
            )

        metric_label: str

        if xml_repr:
            if item:
                metric_label = 'success'
            else:
                metric_label = 'success_fallback'
                metrics.xml2rfc_api_bibitem_hits.labels(
                    xml2rfc_subpath,
                    'success_fallback',
                ).inc()
            resp = HttpResponse(
                xml_repr,
                content_type="application/xml",
                charset="utf-8")

        else:
            metric_label = 'not_found'
            metrics.xml2rfc_api_bibitem_hits.labels(
                xml2rfc_subpath,
                'not_found',
            ).inc()
            resp = JsonResponse({
                "error": {
                    "message":
                        "Error resolving bibliographic item. "
                        "Tried methods: %s"
                        % ', '.join([
                            '{0} ({config}): {error}'.format(
                                method,
                                **method_results[method])
                            for method in methods
                            if method in method_results
                        ])
                }
            }, status=404)

        # Do not increment the metric if it comes from an internal tool.
        if request.headers.get('x-requested-with', None) != 'xml2rfcResolver':
            metrics.xml2rfc_api_bibitem_hits.labels(
                xml2rfc_subpath,
                metric_label,
            ).inc()

        resp.headers['X-Resolution-Methods'] = ';'.join(methods)
        resp.headers['X-Resolution-Outcomes'] = ';'.join([
            (
                '{config},{error}'.format(**method_results[method])
                if method in method_results
                else ''
            )
            for method in methods
        ])

        return resp

    return handle_xml2rfc_path


def _obtain_fallback_xml(subpath: str, anchor: str) -> Union[str, None]:
    """Obtains XML fallback for given subpath, if possible."""

    requested_dirname = subpath.split('/')[-2]
    try:
        actual_dirname = unalias(requested_dirname)
    except ValueError:
        return None
    else:
        subpath = subpath.replace(
            requested_dirname,
            actual_dirname,
            1)
        try:
            xml_repr = Xml2rfcItem.objects.get(subpath=subpath).xml_repr
        except Xml2rfcItem.DoesNotExist:
            return None
        else:
            return _replace_anchor(xml_repr, anchor)


def _replace_anchor(xml_repr: str, anchor: str) -> str:
    """Replace the top-level anchor property with provided anchor.

    Intended to be used with fallback XML that can possibly have
    malformed anchors.

    .. note:: Does not add anchor if it’s missing,
              and does not validate/deserialize given XML."""

    anchor_regex = re.compile(r'anchor=\"([^\"]*)\"')

    return anchor_regex.sub(r'anchor="%s"' % anchor, xml_repr, count=1)
