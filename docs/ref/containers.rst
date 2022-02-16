===========================
Bundled container reference
===========================

The bundled Docker Compose configurations run following containers.
It’s intended as a reference, but could be used in production
as long as :doc:`relevant precautions </howto/run-in-production>` are followed.

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


Monitoring services
===================

Defined in ``docker-compose.monitor.yml``.

.. seealso::

   - :doc:`/howto/run-in-production`
   - :github:`docker-compose.monitor.yml`

**celery-exporter** (third-party)
    Exports Celery-level metrics (number of active tasks, etc.)
    in Prometheus format on port 9808 in internal Docker network.

    - See plain-text metrics via ``<host>:9081/metrics`` on host machine.

**prometheus** (third-party)
    Set up to import metrics from web, celery and celery-exporter.

    - The instance is made available at ``<host>:9090``
      without authentication.

    - You should be able to explore available metrics
      and see health for each of the three targets.

**grafana** (third-party)
    Provisioned with Prometheus container as data source,
    and with dashboards for monitoring GUI and API accesses
    to bibliographic data.

    - You can log in on ``<host>:3000`` using “ietf” as username
      and ``API_SECRET`` provided via the environment as password.

    - Find provisioned dashboards by navigating
      to Dashboards -> Browse -> bibxml or searching dashboards by “bibxml”.

    - The provisioned dashboards do not cover various internal metrics
      provided by Python and Celery, e.g. you can query ``celery_worker_tasks_active{}``
      and so on.

**flower** (third-party)
    Provides a generic GUI for Celery worker monitoring.

    - When you open ``<host>:5555``, you should see current worker status
      and some task-related statistics.
