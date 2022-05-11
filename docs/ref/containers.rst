===========================
Bundled container reference
===========================

The bundled Docker Compose configurations run following containers.
It’s intended as an example, but could be used in production
as long as relevant precautions are taken.

.. seealso:: :doc:`topics/production-setup`, :doc:`howto/run-in-production`

.. note::

   Below, ``<host>`` is used to signify the hostname under which you deploy
   the suite, in case of a local machine it’ll be localhost.
   The Compose configuration automatically binds services
   to host machine’s ports, so that you can explore services
   by pointing to ``<host>:<port>``.


Primary services
================

Defined in ``docker-compose.yml`` (see :github:`docker-compose.yml`).

**web-precheck**
    Builds a base image with Python requirements,
    and launches Django management commands ``migrate`` and ``check --deploy``.

    This container may fail if Django’s deployment checks don’t pass.
    Pay attention to warnings.

**web**
    Serves web GUI using image built by web-precheck.

    - Navigate to ``<host>:8000``, where 8000 is the port number
      provided in your environment, to see service web GUI.

    This container can be run in multiple instances
    (see also :rfp:req:`7`).

**celery**
    Workers that process long-running asynchronous tasks,
    like :term:`indexable source` indexing, using image
    built by web-precheck.

    Celery also spins up a thread
    with Prometheus server exporting metrics on port 9080.

    - You should be able to open ``<host>:9080/metrics``
      to see exported plain-text metrics.

    .. important:: Celery is run with one worker only.

                   Indexing workflows are not currently parallelized,
                   and Prometheus metric export is not adapted
                   for multiple processes.

                   The strongly-recommended way currently
                   is prefork with 1 worker;
                   once better parallelization is implemented,
                   a thread pool can be used after appropriate adjustments
                   to metric exporter.

**celery-exporter** (third-party)
    Exports Celery-level metrics (number of active tasks, etc.)
    in Prometheus format on port 9808 in internal Docker network.

    - See plain-text metrics via ``<host>:9081/metrics`` on host machine.

**db** (third-party)
    Provides a PostgreSQL instance.

    The instance does not store critical data.
    It stores indexed bibliographic items
    and Django session data (relied on by Datatracker OAuth flows).

    .. seealso:: :rfp:req:`4`

    .. important:: No accommodations are currently made
                   for scaling PostgreSQL instance horizontally.

**redis** (third-party)
    Fast simple key-value store used as:

    - Celery task queue backend.

      ``web`` container handles HTTP requests
      and uses Celery client to add tasks to the queue;
      ``celery`` container runs a Celery worker processing that queue.

    - Django cache.


.. _monitoring-containers:

Monitoring services
===================

These containers are included in ``docker-compose.monitor.yml``,
not the main ``docker-compose.yml``.
(It is anticipated
that operations team would want to use Prometheus and Grafana
installations maintained separately.)

You can run multiple Compose configurations in conjunction
with a command like::

    docker compose -f docker-compose.yml -f docker-compose.monitor.yml up

.. seealso::

   - Important note :ref:`about metric collection and CDN caching <metrics-and-cdn>`
   - :github:`docker-compose.monitor.yml` for monitoring service definition

**flower** (third-party)
    Provides a generic GUI for Celery worker monitoring.

    - When you open ``<host>:5555``, you should see current worker status
      and some task-related statistics.

**prometheus** (third-party)
    Set up to import metrics from web, celery and celery-exporter.

    - The instance is made available at ``<host>:9090``
      without authentication.

    - You should be able to explore available metrics
      and see health for each of the three targets.

**grafana** (third-party)
    Provisioned with Prometheus container as data source,
    and with :ref:`dashboards <grafana-dashboards>`
    for monitoring GUI and API accesses
    to bibliographic data.

    - You can log in on ``<host>:3000`` using “ietf” as username
      and ``API_SECRET`` provided via the environment as password.

.. _grafana-dashboards:

Grafana dashboards
------------------

Dashboards with BibXML metrics are automatically provisioned
when ``grafana`` container is created by loading data fixtures.

Provisioned dashboards:

- Can be found by navigating
  to Dashboards -> Browse -> bibxml, or by searching dashboards for “bibxml”.

- Are tied to provided Docker Compose and Prometheus configurations,
  in particular by relying on specific names of Prometheus targets.
  Namely, BibXML metrics query for ``instance`` matching ``web:8000``.

- Are very minimal at the moment,
  and do not cover all metrics available.

  In other words, you can query more metrics than is shown by default
  if you enter a specific metric ID into Grafana query prompt
  (for example, a Celery-level metric such as
  ``celery_worker_tasks_active{}``
  or app-level metric such as ``api_search_hits{}`` or ``gui_search_hits{}``.)

.. seealso::

   - :mod:`prometheus.metrics` for exported app-level metrics
   - :github:`docker-compose.monitor.yml`
     for ``services.grafana.volumes``,
     where Grafana data sources and dashboards are specified,
     and for ``services.prometheus.build.args.TARGET_HOSTS``,
     where Prometheus targets are listed
   - :github:`ops/grafana-dashboard-api-usage.json`
     and :github:`ops/grafana-dashboard-gui-usage.json`
     for Grafana dashboard JSON fixtures
