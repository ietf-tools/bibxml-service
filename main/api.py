"""View functions for API endpoints."""

import json

from django.http import HttpResponse, JsonResponse
from django.conf import settings
from main.exceptions import RefNotFoundError

from .indexed import get_indexed_ref
from .external import get_doi_ref as _get_doi_ref
from .models import RefData


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
        return JsonResponse({"data": result})


def get_doi_ref(request, ref):
    format = request.GET.get('format', 'relaton')
    try:
        result = _get_doi_ref(ref, format)
    except RefNotFoundError:
        return JsonResponse({
            "error": "Unable to find DOI ref {}".format(ref),
        }, status=404)
    else:
        return JsonResponse({"data": result})


def get_ref_by_legacy_path(request, legacy_dataset_name, ref):
    dataset_id = settings.LEGACY_DATASETS.get(
        legacy_dataset_name.lower(),
        None)

    if dataset_id:
        try:
            if dataset_id == 'doi':
                bibxml_repr = get_doi_ref(ref, 'bibxml')
            else:
                bibxml_repr = get_indexed_ref(dataset_id, ref, 'bibxml')

        except RefNotFoundError:
            return JsonResponse({
                "error":
                    "Unable to find BibXML ref {} "
                    "in legacy dataset {} (dataset {})".
                    format(ref, legacy_dataset_name, dataset_id),
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
                format(ref, legacy_dataset_name),
        }, status=404)


def search(request):
    # TODO:
    # implement parsing and validate json request for search fields
    # implement search

    try:
        json_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON decode error"}, status=500)

    fields_values = json_data.get("fields", None)
    dataset = json_data.get("dataset", None)

    offset = json_data.get("offset", "0")
    limit = json_data.get("limit", str(settings.MAX_RECORDS_PER_RESPONSE))

    if isinstance(offset, str) and offset.isdigit():
        offset = int(offset)
    else:
        offset = 0

    if isinstance(limit, str) and limit.isdigit():
        limit = int(limit)
    else:
        limit = settings.MAX_RECORDS_PER_RESPONSE

    if isinstance(fields_values, dict):

        if dataset:
            dataset = dataset.lower()
            total_records = RefData.objects.filter(
                body__contains=fields_values, dataset=dataset
            ).count()

            start = _get_start(total_records, offset)
            end = _get_end(total_records, start + limit)

            result = list(
                RefData.objects.filter(
                    body__contains=fields_values, dataset=dataset
                )
                .order_by("ref")[start:end]
                .values()
            )

        else:
            dataset = None

            total_records = RefData.objects.filter(
                body__contains=fields_values
            ).count()

            start = _get_start(total_records, offset)
            end = _get_end(total_records, start + limit)

            result = list(
                RefData.objects.filter(body__contains=fields_values)
                .order_by("ref")[start:end]
                .values()
            )

    else:
        result = []
        total_records = 0

    return JsonResponse(
        {
            "results": {
                "total_records": total_records,
                "records": len(result),
                "offset": offset,
                "limit": limit,
            },
            "data": result,
        }
    )


def _get_start(total_records, offset):

    if total_records > settings.MAX_RECORDS_PER_RESPONSE:

        if offset <= (total_records - settings.MAX_RECORDS_PER_RESPONSE):
            return offset
        else:
            return total_records - offset

    else:
        if offset < total_records:
            return offset
        else:
            return total_records


def _get_end(total_records, limit):
    if limit > total_records:
        return total_records
    else:
        return limit
