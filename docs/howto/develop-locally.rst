====================================
Set up local development environment
====================================

You will need Docker Desktop with Compose V2 support enabled.

.. note::

   For simplicity and consistency,
   in local development it’s recommended to use Docker Desktop & Docker Compose,
   and currently only that method is covered
   (the old-style conventional way of running under a venv isn’t).

   If you want to run this project directly,
   search ``settings.py`` for ``environ`` occurrences
   and ensure your shell exports the requisite variables.

1. In repository root, create file ``.env`` with following contents::

       PORT=8000
       DB_NAME=indexer
       DB_SECRET=qwert
       DJANGO_SECRET="FDJDSLJFHUDHJCTKLLLCMNII(****#TEFF"
       HOST=localhost
       API_SECRET="test"
       DEBUG=1

   .. seealso:: :doc:`/ref/env`

   .. important::
   
      * Do not use this environment in production. Refer to corresponding operations document.
   
      * ``DB_NAME``, ``DB_SECRET`` values depend on bibxml-indexer runtime environment.
      
        In the basic case, they can match the ones provided in bibxml-indexer environment
        for things to work.
        (This is not ideal:
        bibxml-indexer must have write access to the shared index database,
        while bibxml-service only needs to read from it.
        A separate PostgreSQL user for bibxml-service with read-only access
        would make more sense, but is not currently accommodated
        by Compose configuration.)
   
      * DJANGO_SECRET must be unique.
   
      * DEBUG must not be set to 1 in production.

2. In repository root, run ``docker compose up``.

3. Web front-end should be available under ``localhost:8000``.
   API spec should be available under ``localhost:8000/api/v1``.


Monitoring logs
---------------

::

    docker compose logs -f -t


Invoking Django management commands
-----------------------------------

::

    docker compose exec web bash


Building documentation
======================

1. Under ``docs/``, run ``docker compose up``.

2. Documentation is built in HTML under ``docs/build/html``,
   and is rebuilt on file changes until you stop the container.

3. Documentation will also be served under ``localhost:8001``.
