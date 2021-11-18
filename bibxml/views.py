from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.conf import settings


@require_GET
def openapi_spec(request):
    return render(request, 'openapi.yaml', dict(
        legacy_dataset_ids=list(
            getattr(settings, 'LEGACY_DATASETS', {}).keys()),
    ))
