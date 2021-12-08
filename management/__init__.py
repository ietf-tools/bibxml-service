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
