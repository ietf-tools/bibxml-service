from django.http import HttpResponse, JsonResponse


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

    return JsonResponse({
        "library": lib,
        "ref": ref
    })