==============
BibXML Service
==============

For an overview, see https://github.com/ietf-ribose/bibxml-project.

This project uses Docker, Django and PostgreSQL.

.. note::

   Django settings file makes heavy use of environment variables,
   without which project initialization will fail.
   In local development it’s recommended to use Docker Desktop & Docker Compose,
   and currently only that method is covered
   (the old-style conventional way of running under a venv isn’t).


Running locally using Docker Desktop and Compose
------------------------------------------------

Ensure you are already running bibxml-indexer service (see respective README).
When you use Docker Compose, bibxml-indexer sets up a network
that will be joined by bibxml-service. That network ensures bibxml-service
has access to 

Ensure requisite environment variables are configured in the environment.
For convenience, you can put a file .env with contents like this::

    PORT=8000
    DEBUG=1
    DB_NAME=foo
    DB_SECRET="some-long-random-string"
    DJANGO_SECRET="another-long-random-string"
    HOST=localhost

.. important::

   ``DB_NAME``, ``DB_SECRET`` values depend on bibxml-indexer environment.
   
   In the basic case, they must match the ones provided in bibxml-indexer environment.
   However, this is not ideal:
   bibxml-indexer must have write access to shared database,
   while bibxml-service only reads from it.

   DJANGO_SECRET must be unique.

   DEBUG must not be set to 1 in production.

Then, run ``docker compose up`` from repository root.

To check successful deployment, check http://127.0.0.1:8000/api/v1/.

Invoking Django management commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    % docker compose exec web bash


Credits
-------

Authored by Ribose as produced under the IETF BibXML SOW.
