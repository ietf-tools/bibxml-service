===================
Container reference
===================

The following containers are used at service runtime.

db
--

Provides a PostgreSQL instance used to store citation index.
Data is mounted under ``/data/db`` relative to repository root.

web-precheck
------------

Builds a base image with Python requirements,
and launches Django management commands ``migrate`` and ``check --deploy``.

This container may fail if Django’s deployment checks don’t pass.
Pay attention to warnings.

web
---

Serves web GUI using image built by web-precheck.

celery
------

Workers that process long-running asynchronous tasks,
like citation dataset indexing.

.. note::

   web-precheck, web and celery all run the same Django codebase,
   but in slightly different ways; hence you’ll notice that
   some environment variables (e.g., API_KEY) are not provided to celery container.

redis
-----

Fast simple key-value store used as Celery task queue backend.

flower
------

Provides a generic GUI for Celery worker monitoring.
