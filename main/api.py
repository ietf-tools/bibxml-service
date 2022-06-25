"""View functions for API endpoints."""

from typing import Dict, Any, Optional
from urllib.parse import unquote_plus

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse

from pydantic import ValidationError
from relaton.serializers.bibxml.anchor import get_suitable_anchor
from relaton.models import DocID

from common.pydantic import unpack_dataclasses
from common.util import as_list
from bib_models import BibliographicItem, serializers
from prometheus import metrics
from doi import get_doi_ref as _get_doi_ref

from .search import BaseCitationSearchView
from .query import get_indexed_item
from .query import build_citation_for_docid
from .exceptions import RefNotFoundError
from .types import ExternalBibliographicItem
from . import external_sources


# TODO: Make ``get_doi_ref`` logic part of ``get_by_docid``
def get_doi_ref(request, ref):
    """Retrieves a citation using DOI from Crossref.
    ``format``, ``anchor`` handling equivalent to :func:`get_by_docid`.
    """

    format = request.GET.get('format', 'relaton')

    if format != 'relaton' and format not in serializers.registry:
        return JsonResponse({
            "error": "Requested format is not supported",
        }, status=400)

    parsed_ref = unquote_plus(ref)

    try:
        bibitem = _get_doi_ref(parsed_ref).bibitem

    except RefNotFoundError:
        return JsonResponse({
            "error": "Unable to find DOI ref {}".format(parsed_ref),
        }, status=404)

    except ValidationError as err:
        return JsonResponse({
            "error":
                "Obtained source data doesn’t validate "
                "(err: {})".
                format(str(err)),
        }, status=500)

    else:
        if format == 'relaton':
            return JsonResponse({"data": unpack_dataclasses(bibitem.dict())})
        else:
            kwargs = dict(anchor=request.GET.get('anchor', None))
            serializer = serializers.get(format)
            try:
                bibitem_serialized = serializer.serialize(bibitem, **kwargs)
            except ValueError as err:
                return JsonResponse({
                    "error":
                        "Unable to serialize item {}: "
                        "unsuitable source data (err: {})".
                        format(ref, str(err)),
                }, status=500)
            else:
                return HttpResponse(
                    bibitem_serialized,
                    content_type=serializer.content_type,
                    charset='utf-8')


def get_by_docid(request):
    """Obtains item by ``doctype`` and ``docid`` specified in GET query,
    returns serialized using specified ``format`` (“relaton” by default).

    ``format`` determines response content type.
    (“accepts” header is ignored at this time.)

    ``anchor``, if provided in GET query, is passed to serializer.

    Response has extra header ``X-Xml2rfc-Anchor``
    containing xml2rfc-compatible effective anchor string
    (either given in GET query
    or obtained via
    :func:`relaton.serializers.bibxml.anchor.get_suitable_anchor()`).
    """

    doctype, docid = request.GET.get('doctype', None), request.GET.get('docid')
    format = request.GET.get('format', 'relaton')

    if format != 'relaton' and format not in serializers.registry:
        return JsonResponse({
            "error": "Requested format is not supported",
        }, status=400)

    if not docid:
        return JsonResponse({
            "error": "Missing document ID",
        }, status=400)

    requested_anchor = request.GET.get('anchor', None)

    resp: HttpResponse
    outcome: str

    check_external = (
        request.GET.get('check_external_sources', None) or 'last_resort')

    try:
        try:
            bibitem: BibliographicItem = build_citation_for_docid(
                docid.strip(),
                doctype.strip() if doctype else None,
                strict=True)

        except RefNotFoundError:
            if doctype is not None and check_external == 'last_resort':
                # As a fallback, try external sources.
                sources = [
                    ext_s
                    for ext_s in external_sources.registry.values()
                    if ext_s.applies_to(DocID(id=docid, type=doctype))
                ]
                for ext_s in sources:
                    external_bibitem: Optional[ExternalBibliographicItem]
                    try:
                        external_bibitem = ext_s.get_item(docid)
                    except (RefNotFoundError, RuntimeError):
                        external_bibitem = None
                    else:
                        break
                if external_bibitem:
                    bibitem = external_bibitem.bibitem
                else:
                    # External sources didn’t help
                    raise
            else:
                # Doctype is not specified, so we can’t try external sources.
                raise

    except (RefNotFoundError, AttributeError, IndexError):
        outcome = 'not_found'
        resp = JsonResponse({
            "error":
                "Unable to find bibliographic item matching "
                "document ID {}{}".
                format(docid, f' (type {doctype})' if doctype else ''),
        }, status=404)

    except ValidationError as err:
        outcome = 'validation_error'
        resp = JsonResponse({
            "error":
                "Source data for item {} ({}) didn’t validate "
                "(err: {})".
                format(docid, doctype or "unspecified", str(err)),
        }, status=500)

    else:
        headers = {
            'X-Xml2rfc-Anchor':
                requested_anchor or get_suitable_anchor(bibitem),
        }

        if format == 'relaton':
            outcome = 'success'
            resp = JsonResponse({
                "data": unpack_dataclasses(bibitem.dict()),
            }, headers=headers)
        else:
            serializer = serializers.get(format)
            try:
                bibitem_serialized = serializer.serialize(
                    bibitem,
                    anchor=requested_anchor)
            except ValueError as err:
                outcome = 'serialization_error'
                resp = JsonResponse({
                    "error":
                        "Unable to serialize item {} ({}) "
                        "into requested format: "
                        "unsuitable source data (err: {})".
                        format(docid, doctype or "unspecified", str(err)),
                }, status=500)
            else:
                outcome = 'success'
                resp = HttpResponse(
                    bibitem_serialized,
                    content_type=serializer.content_type,
                    charset='utf-8',
                    headers=headers)

    metrics.api_bibitem_hits.labels(docid, outcome, format).inc()

    return resp


class CitationSearchResultListView(BaseCitationSearchView):
    """Allows to search bibliographic data via API."""

    show_all_by_default = False
    query_in_path = True
    metric_counter = metrics.api_search_hits

    def render_to_response(self, context):
        result_count = len(self.object_list)
        meta: Dict[str, Any] = dict(total_records=result_count)

        page_obj = context['page_obj']
        if page_obj:
            base_url = self.request.build_absolute_uri(self.request.path)
            params = self.request.GET.copy()
            try:
                params.pop('page')
            except KeyError:
                pass
            params_encoded = params.urlencode()

            if page_obj.has_next():
                meta['next'] = "{}?page={}&{}".format(
                    base_url,
                    page_obj.next_page_number(),
                    params_encoded)

            if page_obj.has_previous():
                meta['prev'] = "{}?page={}&{}".format(
                    base_url,
                    page_obj.previous_page_number(),
                    params_encoded)

        return JsonResponse({
            "meta": meta,
            "data": [
                unpack_dataclasses(obj.dict())
                for obj in context['object_list']
            ],
        })


SCHEMA_REFS = {
    'BibliographicItem': BibliographicItem,
}


def json_schema(request, ref: str):
    """Return a JSON Schema for a given reference."""

    if ref not in SCHEMA_REFS:
        return HttpResponseBadRequest("Unknown ref")

    return SCHEMA_REFS[ref].schema_json(indent=2)


def get_ref(request, dataset_name: str, ref: str):
    """Retrieves a reference from dataset by reference.
    Dataset can either be a :attr:`.models.RefData.dataset`
    or an external source ID.
    """

    format = request.GET.get('format', 'relaton')

    try:
        bibitem: BibliographicItem
        if dataset_name in external_sources.registry:
            source = external_sources.registry[dataset_name]
            bibitem = source.get_item(ref.strip()).bibitem
        else:
            indexed_item = get_indexed_item(
                dataset_name,
                ref.strip(),
                strict=False)
            bibitem = indexed_item.bibitem

    except ValidationError:
        return JsonResponse({
            "error":
                "Found ref {} in dataset {} did not validate".
                format(ref, dataset_name),
        }, status=404)

    except RefNotFoundError:
        return JsonResponse({
            "error":
                "Unable to find ref {} in dataset {}".
                format(ref, dataset_name),
        }, status=404)

    else:
        if format == 'relaton':
            return JsonResponse({"data": unpack_dataclasses(bibitem.dict())})

        else:
            kwargs = dict(anchor=request.GET.get('anchor', None))
            serializer = serializers.get(format)

            try:
                bibitem_serialized = serializer.serialize(bibitem, **kwargs)

            except ValueError as err:
                return JsonResponse({
                    "error":
                        "Unable to serialize item {} "
                        "into requested format: "
                        "unsuitable source data (err: {})".
                        format(ref, str(err)),
                }, status=500)

            else:
                return HttpResponse(
                    bibitem_serialized,
                    content_type=serializer.content_type,
                    charset='utf-8')
