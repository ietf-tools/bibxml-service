from django.http import HttpResponse, JsonResponse

from doi2ietf import process_doi_list
import requests_cache

from .models import BibData


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

    print( lib, ref)

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

    elif lib in ['nist']:
        try:
            result = BibData.objects.get(bib_id=ref, bib_type=lib)
            return JsonResponse({
                "data": result.body
            })

        except BibData.DoesNotExist:
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