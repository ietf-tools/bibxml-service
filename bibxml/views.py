from django.http import HttpResponseBadRequest
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from django.shortcuts import render


def openapi_spec(request):
    """Serves machine-readable spec for main API."""
    return render(request, 'openapi.yaml', dict(
        known_dataset_ids=list(
            getattr(settings, 'KNOWN_DATASETS', [])),
    ), content_type='text/x-yaml')


def legacy_openapi_spec(request):
    """Serves machine-readable spec for compatibility/legacy API."""
    return render(request, 'openapi-legacy.yaml', dict(
        legacy_dataset_ids=list(
            getattr(settings, 'LEGACY_DATASETS', {}).keys()),
    ), content_type='text/x-yaml')


def readable_openapi_spec(request, spec: str):
    """Serves human-readable page for given OpenAPI spec
    (provided as a valid arg-free urlpattern name)."""

    try:
        path = reverse(spec)
    except NoReverseMatch:
        raise HttpResponseBadRequest("Invalid spec")
    else:
        return render(request, 'human_readable_openapi_spec.html', dict(
            spec_path=path,
        ))


def readable_openapi_spec_main(request):
    return readable_openapi_spec(request, 'openapi_spec_main')
