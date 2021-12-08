from __future__ import absolute_import

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibxml.settings')

app = Celery('bibxml-indexer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_track_started = True
app.autodiscover_tasks()
