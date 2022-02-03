import logging
import functools
from typing import Callable, List
from enum import Enum

from django.urls import re_path
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from django.http import HttpResponse, JsonResponse

from pydantic import ValidationError

from prometheus import metrics
from bib_models.models import BibliographicItem
from sources.exceptions import RefNotFoundError

from .aliases import unalias
from .models import Xml2rfcItem
from .serializer import to_xml_string


log = logging.getLogger(__name__)


def make_xml2rfc_path_pattern(
        dirnames: List[str],
        fetcher_func: Callable[[str], BibliographicItem]):
    """Constructs Django URL resolver patterns
    for a given list of dirnames.

    Each path is in the shape of
    ``<dirname>/[_]reference.<anchor>.xml``,
    and constructed view delegates bibliographic item
    retrieval to provided fetcher function.

    Fetcher function is passed the ``anchor`` kwarg,
    for which it must return a :class:`BibliographicData` instance,
    and is expected to raise either ``RefNotFoundError``
    or pydantic’s ``ValidationError``.
    """
    return [
        re_path(
            r'(?P<xml2rfc_subpath>%s/'
            r'_?reference\.(?P<anchor>[-A-Za-z0-9./_]+)\.xml'
            r')$'
            % dirname,
            never_cache(require_safe(
                _make_xml2rfc_path_handler(fetcher_func),
            )),
            name='xml2rfc_%s' % dirname)
        for dirname in dirnames
    ]


class Outcome(Enum):
    """Describes the result of locating requested xml2rfc item
    in indexed Relaton sources.
    """
    SUCCESS = 'success'
    NOT_FOUND = 'not_found'
    VALIDATION_ERROR = 'validation_error'
    SERIALIZATION_ERROR = 'serialization_error'


def _make_xml2rfc_path_handler(fetcher_func: Callable[
    [str], BibliographicItem
]):
    """Creates a view function, given a fetcher function.

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
        outcome: Outcome

        try:
            item = fetcher_func(anchor)
        except RefNotFoundError:
            log.error("Item for xml2rfc path not found: %s", xml2rfc_subpath)
            outcome = Outcome.NOT_FOUND
            resp = JsonResponse({
                "error": {
                    "message":
                        "Item for xml2rfc path not found: %s"
                        % xml2rfc_subpath,
                }
            }, status=404)
        except ValidationError:
            log.exception(
                "Item found for xml2rfc path did not validate: %s",
                xml2rfc_subpath)
            outcome = Outcome.VALIDATION_ERROR
            resp = JsonResponse({
                "error": {
                    "message":
                        "Error validating source bibliographic item "
                        "Relaton data",
                }
            }, status=500)
        else:
            try:
                xml_repr = to_xml_string(item, anchor=anchor)
            except ValueError:
                log.exception(
                    "Item found for xml2rfc path did not validate: %s",
                    xml2rfc_subpath)
                outcome = Outcome.SERIALIZATION_ERROR
                resp = JsonResponse({
                    "error": {
                        "message":
                            "Error serializing obtained bibliographic item "
                            "into XML",
                    }
                }, status=500)
            else:
                outcome = Outcome.SUCCESS
                resp = HttpResponse(
                    xml_repr,
                    content_type="application/xml",
                    charset="utf-8")

        if outcome != Outcome.SUCCESS:
            requested_dirname = xml2rfc_subpath.split('/')[-2]
            try:
                actual_dirname = unalias(requested_dirname)
            except ValueError:
                fallback_item = None
            else:
                subpath = xml2rfc_subpath.replace(
                    requested_dirname,
                    actual_dirname,
                    1)
                try:
                    fallback_item = Xml2rfcItem.objects.get(subpath=subpath)
                except Xml2rfcItem.DoesNotExist:
                    fallback_item = None

            if fallback_item is not None:
                metrics.xml2rfc_api_bibitem_hits.labels(
                    xml2rfc_subpath,
                    f'{outcome.name}_fallback',
                ).inc()
                return HttpResponse(
                    fallback_item.xml_repr,
                    content_type="application/xml",
                    charset="utf-8")
            else:
                metrics.xml2rfc_api_bibitem_hits.labels(
                    xml2rfc_subpath,
                    outcome.name,
                ).inc()
                return resp

    return handle_xml2rfc_path
