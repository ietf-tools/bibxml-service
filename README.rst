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

When using Docker Compose, you run bibxml-indexer configuration first,
and it sets up a network that will be joined by bibxml-service
when you run it as the second step. That shared network gives bibxml-service
access to static citation dataset index DB host.

Ensure requisite environment variables are configured in the environment.
For convenience, you can place in repository root a file `.env`
with contents like this::

    PORT=8000
    DEBUG=1
    DB_NAME=foo
    DB_SECRET="some-long-random-string"
    DJANGO_SECRET="another-long-random-string"
    HOST=localhost

.. important::

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

Then, run ``docker compose up`` from repository root.

To check successful deployment, check http://localhost:8000/api/v1/.

Monitoring logs
~~~~~~~~~~~~~~~

::

    % docker compose logs -f -t

Invoking Django management commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    % docker compose exec web bash

After which you are in a shell where you can invoke any ``python manage.py <command>``.


Credits
-------

Authored by Ribose as produced under the IETF BibXML SOW.
