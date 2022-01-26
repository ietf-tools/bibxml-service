"""View functions for API endpoints."""

from urllib.parse import unquote_plus

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.db.models.query import Q
from django.conf import settings

from pydantic import ValidationError

from common.pydantic import unpack_dataclasses
from bib_models.models import BibliographicItem
from bib_models.to_xml import to_xml_string

from .util import BaseCitationSearchView
from .indexed import get_indexed_ref
from .indexed import get_indexed_ref_by_query
from .indexed import build_citation_for_docid
from .external import get_doi_ref as _get_doi_ref
from .exceptions import RefNotFoundError


DEFAULT_LEGACY_REF_PREFIX = 'reference.'

DEFAULT_LEGACY_REF_FORMATTER = (
    lambda legacy_ref:
    legacy_ref[len(DEFAULT_LEGACY_REF_PREFIX):])

DEFAULT_LEGACY_QUERY_BUILDER = (
    lambda legacy_ref:
    Q(ref__iexact=DEFAULT_LEGACY_REF_FORMATTER(legacy_ref)))


def get_ref(request, dataset_name, ref):
    format = request.GET.get('format', 'relaton')
    try:
        result = get_indexed_ref(dataset_name, ref, format)
    except RefNotFoundError:
        return JsonResponse({
            "error":
                "Unable to find ref {} in dataset {}".
                format(ref, dataset_name),
        }, status=404)
    else:
        if format == 'bibxml':
            return HttpResponse(
                result,
                content_type="application/xml",
                charset="utf-8")
        else:
            return JsonResponse({"data": result})


def get_doi_ref(request, ref):
    format = request.GET.get('format', 'relaton')
    if format != 'relaton':
        return JsonResponse({
            "error": "BibXML format is not supported yet by this endpoint",
        }, status=500)
    parsed_ref = unquote_plus(ref)
    try:
        result = _get_doi_ref(parsed_ref)
    except RefNotFoundError:
        return JsonResponse({
            "error": "Unable to find DOI ref {}".format(parsed_ref),
        }, status=404)
    else:
        return JsonResponse({"data": result})


def get_by_docid(request):
    doctype, docid = request.GET.get('doctype', None), request.GET.get('docid')
    format = request.GET.get('format', 'relaton')

    if not docid:
        return HttpResponseBadRequest("Missing document ID")

    try:
        citation = build_citation_for_docid(
            docid.strip(),
            doctype.strip() if doctype else None)
    except RefNotFoundError:
        return JsonResponse({
            "error":
                "Unable to find bibliographic item matching "
                "document ID {} (type {})".
                format(docid, doctype or "unspecified"),
        }, status=404)
    except ValidationError as err:
        return JsonResponse({
            "error":
                "Unable to generate XML for item {} ({}): "
                "malformed source data (err: {})".
                format(docid, doctype or "unspecified", str(err)),
        }, status=500)
    else:
        if format == 'bibxml':
            try:
                xml_string = to_xml_string(citation)
            except ValueError as err:
                return JsonResponse({
                    "error":
                        "Unable to generate XML for item {} ({}): "
                        "unsuitable source data (err: {})".
                        format(docid, doctype or "unspecified", str(err)),
                }, status=500)
            else:
                return HttpResponse(
                    xml_string,
                    content_type="application/xml",
                    charset="utf-8")
        else:
            return JsonResponse({"data": unpack_dataclasses(citation.dict())})


def get_ref_by_legacy_path(request, legacy_dataset_name, legacy_reference):
    legacy_ds_id_or_config = settings.LEGACY_DATASETS.get(
        legacy_dataset_name.lower(),
        None)

    if legacy_ds_id_or_config:

        if hasattr(legacy_ds_id_or_config, 'get'):
            dataset_id = legacy_ds_id_or_config['dataset_id']
            path_prefix = legacy_ds_id_or_config.get(
                'path_prefix',
                DEFAULT_LEGACY_REF_PREFIX)
            ref_formatter = (
                legacy_ds_id_or_config.get('ref_formatter', None) or
                (lambda legacy_ref: legacy_reference[len(path_prefix):]))
            query_builder = (
                legacy_ds_id_or_config.get('query_builder', None) or
                (lambda legacy_ref:
                    Q(ref__iexact=ref_formatter(legacy_ref))))
        else:
            dataset_id = legacy_ds_id_or_config
            ref_formatter = DEFAULT_LEGACY_REF_FORMATTER
            query_builder = DEFAULT_LEGACY_QUERY_BUILDER

        parsed_legacy_ref = unquote_plus(legacy_reference)
        parsed_ref = ref_formatter(parsed_legacy_ref)

        try:
            if dataset_id == 'doi':
                bibxml_repr = _get_doi_ref(parsed_ref, 'bibxml')
            else:
                bibxml_repr = get_indexed_ref_by_query(
                    dataset_id,
                    query_builder(parsed_legacy_ref),
                    'bibxml')

        except RefNotFoundError:
            return JsonResponse({
                "error":
                    "Unable to find BibXML ref {} "
                    "in legacy dataset {} (dataset {})".
                    format(parsed_ref, legacy_dataset_name, dataset_id),
            }, status=404)

        else:
            return HttpResponse(
                bibxml_repr,
                content_type="application/xml",
                charset="utf-8")

    else:
        return JsonResponse({
            "error":
                "Unable to find ref {}: "
                "legacy dataset {} is unknown".
                format(legacy_reference, legacy_dataset_name),
        }, status=404)


class CitationSearchResultListView(BaseCitationSearchView):
    show_all_by_default = False
    query_in_path = True

    def render_to_response(self, context):
        meta = dict(total_records=len(self.object_list))

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
