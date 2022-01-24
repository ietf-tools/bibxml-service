import time
from django.conf import settings
from django.db import connection


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
    def __init__(self):
        self.queries = []

    def __call__(self, execute, sql, params, many, context):
        start = time.monotonic()

        result = execute(sql, params, many, context)

        self.queries.append(dict(
          sql=sql,
          params=params,
          time=time.monotonic() - start,
        ))

        return result
