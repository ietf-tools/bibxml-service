import prometheus_client
from django.http import HttpResponse


def metrics(request):
    """A simple view that exports Prometheus metrics.

    .. important:: The use of the global registry assumes
                   no multiprocessing
                   (i.e., run only one ASGI/WSGI/Celery worker per machine.)
    """

    registry = prometheus_client.REGISTRY
    metrics_page = prometheus_client.generate_latest(registry)
    return HttpResponse(
        metrics_page,
        content_type=prometheus_client.CONTENT_TYPE_LATEST,
    )
