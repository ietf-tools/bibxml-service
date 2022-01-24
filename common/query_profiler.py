import time
import logging
from django.conf import settings
from django.db import connection


log = logging.getLogger(__name__)


def context_processor(request):
    """Adds ``query_times`` template variable,
    using either ``request._queries`` if provided by middleware
    or ``connection.queries`` (is empty without DEBUG) if not.
    """

    if hasattr(request, '_queries'):
        # Without DEBUG on, we may have middleware populate queries
        queries = request._queries
    else:
        queries = connection.queries
    return dict(
        profiling=dict(
            query_times=[str(p['time'])[:5] for p in queries],
        ),
    )


def middleware(get_response):
    """Unless DEBUG is on, runs query profiler against each request
    and places results under ``request._queries``.
    """

    def middleware(request):
        if not settings.DEBUG:
            profiler = QueryProfiler()
            request._queries = profiler.queries

            with connection.execute_wrapper(profiler):
                return get_response(request)

        else:
            return get_response(request)

    return middleware


class QueryProfiler:
    """
    Use as follows::

        profiler = QueryProfiler()

        with connection.execute_wrapper(ql):
            do_queries()

        # Here, profiler.queries is populated.

    """
    def __init__(self, warning_threshold_sec=4):
        self.queries = []
        self.warning_threshold_sec = warning_threshold_sec

    def __call__(self, execute, sql, params, many, context):
        start = time.monotonic()

        result = execute(sql, params, many, context)

        elapsed_seconds = time.monotonic() - start
        self.queries.append(dict(
          sql=sql,
          params=params,
          time=elapsed_seconds,
        ))

        if elapsed_seconds > self.warning_threshold_sec:
            log.warning(
                "Query took %s seconds (too long): %s (params %s)",
                str(elapsed_seconds)[:5],
                sql, repr(params))

        return result
