from django.db import connection


def profiling(request):
    return dict(
        profiling=dict(
            query_times=[p['time'] for p in connection.queries],
        ),
    )
