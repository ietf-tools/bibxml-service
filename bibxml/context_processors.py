from django.conf import settings
from sources.indexable import registry as indexable_sources


def service_meta(request):
    return dict(
        snapshot=settings.SNAPSHOT,
        service_name=settings.SERVICE_NAME,
        repo_url=settings.SOURCE_REPOSITORY_URL,
    )


def matomo(request):
    """Makes the :data:`.settings.MATOMO` available to templates."""
    return dict(
        matomo=getattr(settings, 'MATOMO', None),
    )


def sources(request):
    return dict(
        indexable_sources=indexable_sources.keys(),
        relaton_datasets=settings.RELATON_DATASETS,
        authoritative_datasets=settings.AUTHORITATIVE_DATASETS,
    )
