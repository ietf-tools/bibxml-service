from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def openapi_spec(request):
    return render(request, 'openapi.yaml')
