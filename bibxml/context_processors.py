from django.db import connection
from django.conf import settings


def profiling(request):
    return dict(
        profiling=dict(
            query_times=[p['time'] for p in connection.queries],
        ),
    )


def service_meta(request):
    return dict(
        snapshot=settings.SNAPSHOT,
        service_name=settings.SERVICE_NAME,
    )


def sources(request):
    return dict(
        known_datasets=settings.KNOWN_DATASETS,
        indexed_datasets=[
            ds
            for ds in settings.KNOWN_DATASETS
            if ds not in settings.EXTERNAL_DATASETS],
        external_datasets=settings.EXTERNAL_DATASETS,
        authoritative_datasets=settings.AUTHORITATIVE_DATASETS,
    )
