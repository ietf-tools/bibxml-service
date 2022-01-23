from django.db import connection


def profiling(request):
    return {
        'profiling': {
            'query_times': [p['time'] for p in connection.queries],
        },
    }
