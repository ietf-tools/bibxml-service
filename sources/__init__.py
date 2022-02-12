"""This module implements pluggable data sources.

Currently, it only takes care of Git-based indexable sources
(see :func:`sources.indexable.register_git_source`).

It provides types that focus on bibliographic data sourcing,
but generally a registered indexable source can index any data.
"""

import redis
from .celery import app as celery_app

from django.conf import settings


cache = redis.Redis(
    host=settings.REDIS_HOST,
    port=int(settings.REDIS_PORT),
    charset="utf-8",
    decode_responses=True,
)

__all__ = (
    'celery_app',
    'cache',
)
