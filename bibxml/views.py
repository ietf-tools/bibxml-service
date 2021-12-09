from django.shortcuts import render
from django.conf import settings


def openapi_spec(request):
    return render(request, 'openapi.yaml', dict(
        known_dataset_ids=list(
            getattr(settings, 'KNOWN_DATASETS', [])),
    ), content_type='text/x-yaml')


def legacy_openapi_spec(request):
    return render(request, 'openapi-legacy.yaml', dict(
        legacy_dataset_ids=list(
            getattr(settings, 'LEGACY_DATASETS', {}).keys()),
    ), content_type='text/x-yaml')
