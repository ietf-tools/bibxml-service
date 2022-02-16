"""View functions for API endpoints."""

from typing import Dict, Any
from urllib.parse import unquote_plus

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse

from pydantic import ValidationError

from common.pydantic import unpack_dataclasses
from bib_models.models.bibdata import BibliographicItem
from bib_models import serializers
from prometheus import metrics

from doi import get_doi_ref as _get_doi_ref

from .search import BaseCitationSearchView
from .query import get_indexed_ref
from .query import build_citation_for_docid
from .exceptions import RefNotFoundError
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

    resp: HttpResponse
    outcome: str

    try:
        composite_bibitem = build_citation_for_docid(
            docid.strip(),
            doctype.strip() if doctype else None)

        # This will be the latest sourced item.
        bibitem = list(composite_bibitem.sources.values())[0].bibitem

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
                "Found item {} ({}), but source data didn’t validate "
                "(err: {})".
                format(docid, doctype or "unspecified", str(err)),
        }, status=500)

    else:
        if format == 'relaton':
            outcome = 'success'
            resp = JsonResponse({"data": unpack_dataclasses(bibitem.dict())})
        else:
            kwargs = dict(anchor=request.GET.get('anchor', None))
            serializer = serializers.get(format)
            try:
                bibitem_serialized = serializer.serialize(bibitem, **kwargs)
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
                    charset='utf-8')

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


def get_ref(request, dataset_name, ref):
    """Retrieve a reference from dataset by reference.
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
            data: Dict[str, Any] = get_indexed_ref(
                dataset_name,
                ref.strip(),
                'relaton')
            bibitem = BibliographicItem(**data)

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
