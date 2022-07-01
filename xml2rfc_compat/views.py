from typing import cast, Tuple, Optional, TypedDict, Dict
import re
import logging

from pydantic import ValidationError

from django.http import HttpResponse, HttpResponseNotFound, JsonResponse

from bib_models import BibliographicItem
from prometheus import metrics

from main.exceptions import RefNotFoundError
from main.query import build_citation_for_docid

from .models import Xml2rfcItem
from .adapters import Xml2rfcAdapter, adapters
# from .resolvers import AnchorFormatterFunc, anchor_formatter_registry
from .serializer import to_xml_string
from .aliases import unalias


log = logging.getLogger(__name__)


__all__ = (
    'handle_xml2rfc_path',
    'resolve_manual_map',
    'resolve_automatically',
    'obtain_fallback_xml',
    'ResolutionOutcome',
    '_replace_anchor',
)


def resolve_manual_map(subpath: str) -> Tuple[
    Optional[str],
    Optional[BibliographicItem],
    Optional[str],
]:
    """Returns a 3-tuple of mapping configuration, resolved item,
    and error as a string, any can be None.
    Does not raise exceptions.
    """
    mapped_docid: Optional[str]
    resolved_item: Optional[BibliographicItem]
    error: Optional[str]
    try:
        manual_map = Xml2rfcItem.objects.get(subpath=subpath)
    except Xml2rfcItem.DoesNotExist:
        mapped_docid = None
        resolved_item = None
        error = "not found"
    else:
        mapped_docid = (
            (manual_map.sidecar_meta or {}).
            get('primary_docid', None))

        if mapped_docid is None:
            resolved_item = None
            error = "not mapped"
        else:
            try:
                resolved_item = build_citation_for_docid(
                    cast(str, mapped_docid))
            except ValidationError:
                log.exception(
                    "Unable to validate item "
                    "manually mapped to xml2rfc path %s "
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
    adapter: Xml2rfcAdapter,
) -> Tuple[
    str,
    Optional[BibliographicItem],
    Optional[str],
]:
    """Returns a 3-tuple of resolver function name, resolved item,
    and error as a string, any can be None.
    Does not raise exceptions.
    """
    item: Optional[BibliographicItem] = None
    error: Optional[str] = None
    try:
        item = adapter.resolve()
    except RefNotFoundError as e:
        log.exception(
            "Unable to resolve xml2rfc path automatically: %s",
            subpath)
        error = f"not found ({str(e)})"
    except ValidationError:
        log.exception(
            "Item found for xml2rfc path did not validate: %s",
            subpath)
        error = "validation problem"
    except Exception:
        log.exception(
            "Failed to automatically resolve item for path: %s",
            subpath)
        error = "uncategorized issue"

    config_str = adapter.__class__.__name__
    try:
        config_str = '%s: %s' % (
            config_str,
            ' -> '.join([i.replace(',', ' ') for i in adapter._log])
        )
    except Exception:
        pass
    return config_str, item, error


class ResolutionOutcome(TypedDict, total=True):
    config: str
    error: str


def handle_xml2rfc_path(
    request,
    xml2rfc_subpath: str,
    dirname: str,
    anchor: str,
):
    """View function that resolves an xml2rfc path.

    Requires an :term:`xml2rfc adapter` to be registered for given
    ``dirname``.
    Adapter’s ``resolve()`` method will only be called
    if manual map was not found or did not resolve successfully.

    This function handles filename
    cleanup, obtaining a :class:`relaton.models.bibdata.BibliographicItem`
    instance, serializing it into an XML string with proper anchor tag supplied,
    incrementing relevant metrics.

    The view function behaves as following
    (see also :ref:`xml2rfc-path-resolution-algorithm`):

    - Inspects ``X-Requested-With`` request header, and does not increment
      access metric if it’s the internal ``xml2rfcResolver`` tool.

    - The ``anchor`` component of URL pattern
      (see :data:`xml2rfc_compat.models.dir_subpath_regex`)
      is always used when attempting to auto-resolve to Relaton resource,
      and *may* be used by anchor formatter
      to obtain the value of ``anchor`` attributes in resulting XML.

    :returns:

      - In case of success, ``application/xml`` response
        with custom headers aiming to simplify troubleshooting path resolution:

        ``X-Resolution-Methods``
            semicolon-separated string of resolution methods tried.

        ``X-Resolution-Outcome``
            semicolon-separated string of resolution outcomes.
            Each tried outcome is a comma-separated string
            “method configuration,error info”.

            Substrings can be empty, e.g. if method was not tried,
            there was no error, not configuration, etc.

        .. note::

           - The ``anchor`` *XML attribute value* is generated according
             to the logic in :mod:`xml2rfc_compat.serializer`
             and may not match anchor given in URL pattern string.

           - The optional ``anchor`` passed *as GET parameter*
             will override ``anchor`` attribute in XML.

      - In case of failure (and no fallback available),
        ``application/json`` response with error description.
    """
    resp: HttpResponse

    item: Optional[BibliographicItem] = None
    xml_repr: Optional[str] = None

    requested_anchor = request.GET.get('anchor', None)

    normalized_dirname = unalias(dirname)

    try:
        adapter_cls = adapters[normalized_dirname]
    except KeyError:
        return HttpResponseNotFound("No xml2rfc adapter for %s", dirname)

    # Below code attempts to catch anything
    # and return fallback XML in any problematic scenario.

    adapter = adapter_cls(xml2rfc_subpath, normalized_dirname, anchor)

    methods = ["manual", "auto", "fallback"]
    method_results: Dict[str, ResolutionOutcome] = {}

    mapped_docid, item, error = resolve_manual_map(xml2rfc_subpath)
    if mapped_docid:
        method_results['manual'] = dict(
            config=mapped_docid,
            error='' if item else (error or "no error information"),
        )

    if not item:
        config, item, error = resolve_automatically(
            xml2rfc_subpath,
            anchor,
            adapter)
        method_results['auto'] = dict(
            config=config,
            error='' if item else (error or "no error information"),
        )

    try:
        if adapter_anchor := adapter.format_anchor():
            requested_anchor = adapter_anchor
    except Exception:
        log.exception(
            "xml2rfc path (%s): "
            "Adapter failed at format_anchor()",
            xml2rfc_subpath)

    if item:
        try:
            xml_repr = to_xml_string(item, anchor=requested_anchor)
        except Exception:
            log.exception(
                "xml2rfc path (%s): "
                "Failed to serialize resolved item, "
                "attempting fallback",
                xml2rfc_subpath)

    if not xml_repr:
        xml_repr = obtain_fallback_xml(
            xml2rfc_subpath,
            anchor=requested_anchor)
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

        # It would be more consistent to return a plain-text 404,
        # but API declares a JSON response so…
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


def obtain_fallback_xml(
    subpath: str,
    anchor: Optional[str] = None,
) -> Optional[str]:
    """Obtains XML fallback for given subpath, if possible.

    Does not raise exceptions.
    """

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
            if anchor:
                return _replace_anchor(xml_repr, anchor)
            else:
                return xml_repr


def _replace_anchor(xml_repr: str, anchor: str) -> str:
    """Replace the top-level anchor property with provided anchor.

    Intended to be used with fallback XML that can possibly have
    malformed anchors.

    .. note:: Does not add anchor if it’s missing,
              and does not validate/deserialize given XML."""

    anchor_regex = re.compile(r'anchor=\"([^\"]*)\"')

    return anchor_regex.sub(r'anchor="%s"' % anchor, xml_repr, count=1)
