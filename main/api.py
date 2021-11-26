"""View functions for API endpoints."""

from urllib.parse import unquote_plus

from django.http import HttpResponse, JsonResponse
from django.db.models.query import QuerySet
from django.conf import settings
from django.views.generic.list import BaseListView

from main.exceptions import RefNotFoundError

from .indexed import get_indexed_ref, search_refs
from .external import get_doi_ref as _get_doi_ref
from .models import RefData


DEFAULT_LEGACY_REF_PREFIX = 'reference.'


def index(request):
    """Serves API index."""

    return HttpResponse("""
        <!DOCTYPE html>
        <html>
          <head>
            <title>API documentation</title>

            <meta charset="utf-8"/>
            <meta name="viewport"
                content="width=device-width,
                initial-scale=1">

            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">

            <style>
              body {
                margin: 0;
                padding: 0;
              }
            </style>
          </head>
          <body>
            <redoc spec-url='/openapi.yaml'></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
          </body>
        </html>
    """)


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
    try:
        parsed_ref = unquote_plus(ref)
        result = _get_doi_ref(parsed_ref, format)
    except RefNotFoundError:
        return JsonResponse({
            "error": "Unable to find DOI ref {}".format(parsed_ref),
        }, status=404)
    else:
        return JsonResponse({"data": result})


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
            get_ref_from_legacy_ref = (
                legacy_ds_id_or_config.get('ref_formatter', None) or
                (lambda legacy_ref: legacy_reference[len(path_prefix):]))
        else:
            dataset_id = legacy_ds_id_or_config
            get_ref_from_legacy_ref = (
                lambda legacy_ref:
                    legacy_reference[len(DEFAULT_LEGACY_REF_PREFIX):])

        parsed_legacy_ref = unquote_plus(legacy_reference)
        parsed_ref = get_ref_from_legacy_ref(parsed_legacy_ref)

        try:
            if dataset_id == 'doi':
                bibxml_repr = _get_doi_ref(parsed_ref, 'bibxml')
            else:
                bibxml_repr = get_indexed_ref(dataset_id, parsed_ref, 'bibxml')

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


class CitationSearchResultListView(BaseListView):
    model = RefData
    paginate_by = 20

    def get_queryset(self) -> QuerySet[RefData]:
        query = self.kwargs.get('query', None)
        if query:
            return search_refs(unquote_plus(query))
        else:
            return RefData.objects.none()

    def render_to_response(self, context):
        meta = dict(total_records=self.object_list.count())

        page_obj = context['page_obj']
        if page_obj:
            base_url = self.request.build_absolute_uri(self.request.path)
            if page_obj.has_next():
                meta['next'] = "{}?page={}".format(
                    base_url,
                    page_obj.next_page_number())
            if page_obj.has_previous():
                meta['prev'] = "{}?page={}".format(
                    base_url,
                    page_obj.previous_page_number())

        return JsonResponse({
            "meta": meta,
            "data": [obj.body for obj in context['object_list']],
        })
