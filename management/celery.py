"""When run as a web service,
this module provides an API for adding tasks to the queue.

When run as Celery worker, this module sets up
Celery to discover Django settings and task queue,
and a signal listener that runs a simple HTTP server in a thread
to export Celery-level Prometheus metrics."""

from __future__ import absolute_import

import os
from celery import Celery
from celery.signals import worker_process_init
from prometheus_client import start_http_server

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibxml.settings')

app = Celery('bibxml-indexer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_track_started = True
app.autodiscover_tasks()


@worker_process_init.connect
def start_prometheus_exporter(*args, **kwargs):
    """Starts Prometheus exporter when worker process initializes.

    .. important::

       **No accommodations are made for multiprocessing mode.**

       Prometheus support for multi-process export is finicky,
       not so great, and not enabled.

       This handler should break your setup if you run more than
       one worker process
       (since the first process should occupy the port below),
       and this is left intentional.

       Key takeaway is:

       - Don’t run Celery in default worker mode (prefork)
         with more than one worker.
         It’ll be a problem for other reasons than Prometheus export,
         unless tasks are properly parallelized.
       - Once parallelized into smaller I/O bound tasks,
         switch to eventlet/gevent pooling,
         and use the appropriate signal (possibly ``celeryd_init``)
         for Prometheus exporter service startup.
    """
    start_http_server(9080)
