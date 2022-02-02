===========================================
How to set up local development environment
===========================================

You will need Docker Desktop with Compose V2 support enabled.

.. note::

   For simplicity and consistency,
   in local development it’s recommended to use Docker & Docker Compose,
   and currently only that method is covered
   (the old-style conventional way of running under a venv isn’t).

   If you want to run this project directly,
   see :doc:`/ref/env` for environment variables,
   some of which are required by Django and need to be exported
   in your shell before you start the development server.

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
       SERVICE_NAME="IETF BibXML service"
       CONTACT_EMAIL="<ops contact email>"
       DEBUG=1

   .. seealso:: :doc:`/ref/env`

   .. important:: This environment is not suitable for production use.

2. In repository root, run ``docker compose build``.


Building documentation
======================

Make sure to build base image first (see above).

1. Under ``docs/``, run ``docker compose up``.

2. Documentation is built in HTML under ``docs/build/html``,
   and is rebuilt whenever project files change
   until you stop the container.

3. HTML documentation is served under ``localhost:8001``.


Running the service
===================

To simply serve the BibXML service, run ``docker compose up``.

Web front-end should be available under ``localhost:8000``.
API spec should be available under ``localhost:8000/api/v1``.

If you plan on making changes *and* you set DEBUG=1 in your environment,
for better development experience you can run the command this way instead::

    docker compose -f docker-compose.yml -f docker-compose.dev.yml up

This will mount source code directory and enable hot reload on changes.


Monitoring logs
---------------

::

    docker compose logs -f -t


Invoking Django management commands
-----------------------------------

::

    docker compose exec web bash
