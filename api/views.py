from django.http import HttpResponse, JsonResponse

from doi2ietf import process_doi_list
import requests_cache

from .models import RefData

from django.conf import settings


def index(request):
    return HttpResponse("API v1 index, use search or ref")


def search(request):
    # TODO: 
    # implement parsing and validate json request for search fields
    # implement search

    if request.method == 'POST':
        return JsonResponse({
            "results":  []
        })
    else:
        return JsonResponse({
                "error": "Bad HTTP method"
            },
            status=405
        )

def get_ref(request, lib, ref):
    # TODO:
    # implement getting referense from lib by lib, ref
    # implement convertation 

    if lib == "doi":
        result = get_doi_refs(ref)

        if result:
            result = result[0]['a'] # TODO: ask about enumerating

            return JsonResponse({
                "data": result
            })

        else:
            return JsonResponse({
                "error": "Unable to get DOI %s" % ref
            }, status=404)

    elif lib in settings.INDEXABLE_DATASETS:
        try:
            result = RefData.objects.get(ref_id=ref, dataset=lib)
            return JsonResponse({
                "data": result.body
            })

        except RefData.DoesNotExist:
            return JsonResponse({
                "error": "Not Found Ref.: %s at Lib: %s" % (ref, lib.upper())
            }, status=404)

    else:
        return JsonResponse({
            "error": "%s Is Not Implemented" % lib.upper()
        }, status=404)


def get_doi_refs(ref):
    with requests_cache.enabled():
        return process_doi_list([ref], 'DICT')