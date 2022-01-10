====================================
Set up local development environment
====================================

You will need Docker Desktop with Compose V2 support enabled.

.. note::

   For simplicity and consistency,
   in local development it’s recommended to use Docker & Docker Compose,
   and currently only that method is covered
   (the old-style conventional way of running under a venv isn’t).

   If you want to run this project directly,
   search ``settings.py`` for ``environ`` occurrences
   and ensure your shell exports the requisite variables.

.. note::

   Commands below presume you use Docker Desktop with Docker Compose V2 support.

   - If you have installed Docker Compose separately under ``docker-compose`` binary,
     replace ``docker compose`` with ``docker-compose``.

   - Depending on your OS and installation method,
     you may also need to prepend Compose commands with ``sudo``.


Building base image
===================

.. note::

   Building base image is necessary both for running the service and building the docs,
   although full ``.env`` may not be strictly necessary if you only want to build the docs.

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

2. In repository root, run ``docker compose build``.


Building documentation
======================

1. Under ``docs/``, run ``docker compose up``.

2. Documentation is built in HTML under ``docs/build/html``,
   and is rebuilt whenever project files change
   until you stop the container.

3. HTML documentation is served under ``localhost:8001``.


Running the service
===================

To simply serve the BibXML service, run ``docker compose up``.

If you plan on making changes,
instead for better development experience run::

    docker compose -f docker-compose.yml -f docker-compose.dev.yml up

This will mount source code directory and enable hot reload on changes.

Web front-end should be available under ``localhost:8000``.
API spec should be available under ``localhost:8000/api/v1``.


Monitoring logs
---------------

::

    docker compose logs -f -t


Invoking Django management commands
-----------------------------------

::

    docker compose exec web bash
