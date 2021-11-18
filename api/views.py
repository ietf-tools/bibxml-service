import json
import requests_cache
from doi2ietf import process_doi_list

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings

from .models import RefData


@require_GET
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


@require_POST
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


@require_GET
def get_ref(request, dataset_name, ref):
    try:
        result = RefData.objects.get(ref=ref, dataset=dataset_name)
        return JsonResponse({"data": result.body})

    except RefData.DoesNotExist:
        return JsonResponse({
            "error":
                "Unable to find ref {} in dataset {}".
                format(ref, dataset_name),
        }, status=404)


@require_GET
def get_doi_ref(request, ref):
    try:
        result = _get_doi_ref(ref)
    except DOINotFoundError:
        return JsonResponse({
            "error": "Unable to find DOI ref {}".format(ref),
        }, status=404)
    else:
        return JsonResponse({
            "data": result
        })


def _get_doi_ref(ref):
    with requests_cache.enabled():
        doi_list = process_doi_list([ref], "DICT")
        if len(doi_list) > 0:
            # TODO: What to do with multiple DOI results for a reference?
            return doi_list[0]["a"]
        else:
            raise DOINotFoundError("Reference not found: got empty list from DOI", ref)


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


class DOINotFoundError(RuntimeError):
    """DOI reference not found.

    :param doi_ref string: DOI reference that was not found."""

    def __init__(self, message, doi_ref):
        super().__init__(message)
        self.doi_ref = doi_ref


@require_GET
def get_legacy_ref(request, legacy_dataset_name, legacy_ref):
    dataset_id = settings.LEGACY_DATASETS.get(legacy_dataset_name, None)

    if dataset_id:
        try:
            result = RefData.objects.get(ref=legacy_ref, dataset=dataset_id)
            bibxml_repr = result.representations.get('bibxml', None)

            if bibxml_repr is not None:
                return HttpResponse(
                    bibxml_repr,
                    content_type="application/xml",
                    charset="utf-8")

            else:
                return JsonResponse({
                    "error":
                        "Missing BibXML representation for ref {} "
                        "in legacy dataset {} (dataset {})".
                        format(legacy_ref, legacy_dataset_name, dataset_id),
                }, status=404)

        except RefData.DoesNotExist:
            return JsonResponse({
                "error":
                    "Unable to find ref {} "
                    "in legacy dataset {} (dataset {})".
                    format(legacy_ref, legacy_dataset_name, dataset_id),
            }, status=404)
    else:
        return JsonResponse({
            "error":
                "Unable to find ref {}: "
                "legacy dataset {} is unknown".
                format(legacy_ref, legacy_dataset_name),
        }, status=404)
