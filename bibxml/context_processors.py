from django.conf import settings


def service_meta(request):
    return dict(
        snapshot=settings.SNAPSHOT,
        service_name=settings.SERVICE_NAME,
    )


def matomo(request):
    return dict(
        matomo=getattr(settings, 'MATOMO', None),
    )


def sources(request):
    return dict(
        known_datasets=[
            *settings.RELATON_DATASETS,
            *settings.EXTERNAL_DATASETS,
        ],
        relaton_datasets=settings.RELATON_DATASETS,
        external_datasets=settings.EXTERNAL_DATASETS,
        authoritative_datasets=settings.AUTHORITATIVE_DATASETS,
    )
