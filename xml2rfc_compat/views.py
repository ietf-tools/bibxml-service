from typing import Tuple, Optional, TypedDict, Dict, Callable, Union
import re
import logging

from pydantic import ValidationError

from django.http import HttpResponse, HttpResponseNotFound, JsonResponse

from bib_models import BibliographicItem
from prometheus import metrics

from main.exceptions import RefNotFoundError

from .models import Xml2rfcItem, construct_normalized_xml2rfc_subpath
from .adapters import Xml2rfcAdapter, adapters
# from .resolvers import AnchorFormatterFunc, anchor_formatter_registry
from .serializer import to_xml_string
from .aliases import unalias


log = logging.getLogger(__name__)


__all__ = (
    'handle_xml2rfc_path',
    'resolve_mapping',
    'resolve_automatically',
    'obtain_fallback_xml',
    'ResolutionOutcome',
    '_replace_anchor',
)


def resolve_mapping(
    subpath: str,
    adapter: Xml2rfcAdapter,
) -> Tuple[
    Optional[BibliographicItem],
    Optional[str],
]:
    """Returns a 2-tuple of resolved item,
    and error as a string, any can be None.
    Does not raise exceptions.

    .. important::

       If a mapping for ``reference.foo.bar.xml``
       should apply for ``_reference.foo.bar.xml``,
       then ``subpath`` should be normalized
       stripping the possible underscore in ``_reference``.
    """
    resolved_item: Optional[BibliographicItem]
    error: Optional[str]

    try:
        resolved_item = adapter.resolve_mapped()
    except Xml2rfcItem.DoesNotExist:
        resolved_item = None
        error = "not a legacy path or not indexed"
    except RefNotFoundError:
        log.exception(
            "Unable to resolve an item for xml2rfc path %s, "
            "despite it being mapped",
            subpath)
        error = "not found"
        resolved_item = None
    except ValidationError:
        log.exception(
            "Unable to validate item "
            "mapped to xml2rfc path %s",
            subpath)
        error = "validation problem"
        resolved_item = None
    else:
        error = None

    return resolved_item, error


def resolve_automatically(
    subpath: str,
    anchor: str,
    adapter: Xml2rfcAdapter,
) -> Tuple[
    Optional[BibliographicItem],
    Optional[str],
]:
    """
    This function does really nothing except invoking
    given adapter instance’s ``resolve()``
    method with proper error handling and logging.

    Returns a 2-tuple of resolved item,
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

    return item, error


class ResolutionOutcome(TypedDict, total=True):
    config: str
    error: str


def handle_xml2rfc_path(
    request,
    xml2rfc_subpath: str,
    dirname: str,
    anchor: str,
) -> Union[
    HttpResponse,
    JsonResponse
]:
    """View function that resolves an xml2rfc path.

    Requires an :term:`xml2rfc adapter` to be registered for given
    ``dirname``.
    Adapter’s ``resolve()`` method will only be called
    if manual map was not found or did not resolve successfully.

    This function handles filename
    cleanup, obtaining a :class:`relaton.models.bibdata.BibliographicItem`
    instance, serializing it into an XML string with proper anchor tag,
    incrementing relevant metrics.

    Notable aspects of this view’s behavior:

    - When resolving a mapped Relaton resource or fallback XML,
      normalized xml2rfc subpath is used
      (for example, it never has an underscore before the ``reference.`` part).

      However, full xml2rfc subpath is used when logging
      or when incrementing access metrics.

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
        ``application/json`` response with error description

    .. seealso:: :ref:`xml2rfc-path-resolution-algorithm`
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

    subpath_normalized = construct_normalized_xml2rfc_subpath(dirname, anchor)

    adapter = adapter_cls(xml2rfc_subpath, normalized_dirname, anchor)

    methods = ["manual", "auto", "fallback"]
    method_results: Dict[str, ResolutionOutcome] = {}

    item, error = resolve_mapping(subpath_normalized, adapter)
    if item:
        method_results['manual'] = dict(
            config=adapter.format_log(),
            error='' if item else (error or "no error information"),
        )
    else:
        item, error = resolve_automatically(
            xml2rfc_subpath,
            anchor,
            adapter)
        method_results['auto'] = dict(
            config=adapter.format_log(),
            error='' if item else (error or "no error information"),
        )

    try:
        # format_anchor() should be called after attempts to resolve the item
        if not requested_anchor and (_anch := adapter.format_anchor()):
            requested_anchor = _anch
    except Exception:
        log.exception(
            "xml2rfc path (%s): "
            "Adapter failed at format_anchor()",
            xml2rfc_subpath)

    if item:
        try:
            xml_repr = to_xml_string(
                item,
                anchor=requested_anchor,
            ).decode('utf-8')  # relaton-py’s serializer encodes.
        except Exception:
            log.exception(
                "xml2rfc path (%s): "
                "Failed to serialize resolved item, "
                "attempting fallback",
                xml2rfc_subpath)

    if not xml_repr:
        xml_repr = obtain_fallback_xml(
            subpath_normalized,
            anchor=requested_anchor)
        method_results['fallback'] = dict(
            config='',
            error='' if xml_repr else "not indexed",
        )

    metric_label: str

    if xml_repr:
        xml_repr = _replace_anchor(
            xml_repr,
            lambda anchor: adapter.mangle_anchor(anchor),
        )

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

    .. note:: You may want to normalize ``subpath``
              to remove the possible underscore in ``_reference``.
              This would mean fallback response for ``_reference.foo.bar.xml``
              can use XML from ``reference.foo.bar.xml``, if it exists.
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


anchor_regex = re.compile(r'anchor=\"([^\"]*)\"')
"""Regular expression used for mangling anchor in an XML string."""


def _replace_anchor(xml_repr: str, anchor: str | Callable[[str], str]) -> str:
    """Replace the top-level anchor property with provided anchor.

    Intended to be used with XML string that could possibly have
    malformed anchors.

    :param anchor:
        Either a string (anchor to replace with),
        or a callable that takes an existing anchor and returns a new one.

    .. note:: Does not add anchor if it’s missing,
              and does not validate/deserialize given XML."""

    if not isinstance(anchor, str):
        if match := anchor_regex.search(xml_repr):
            old_anchor = match.group(1)
            try:
                new_anchor = anchor(old_anchor)
            except Exception:
                return xml_repr
        else:
            return xml_repr
    else:
        new_anchor = anchor

    return anchor_regex.sub(
        r'anchor="%s"' % new_anchor,
        xml_repr,
        count=1)
