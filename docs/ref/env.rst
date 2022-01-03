==============================
Environment variable reference
==============================

Environment variables read by Docker Compose
============================================

The following variables are read from the environment
(either shell where you execute ``docker compose``
or ``.env`` file, consult Compose docs for more information).

Most of them are passed to containers’ respective environments.

.. seealso:: :doc:`/howto/develop-locally` for sample development environment

.. seealso:: :doc:`/ref/containers`

``HOST``
    Hostname used for Web GUI.
    HTTP requests with mismatching Host header will result in an error.

``PORT``
    Docker Compose will make Web GUI available
    on the host OS under this port number.

``DB_NAME``
    PostgreSQL database and user name.

``DB_SECRET``
    User password for PostgreSQL server authentication.

``DJANGO_SECRET``
    Django’s secret key.

``API_SECRET``
    Token for management GUI and API access.

``DEBUG``
    If set to 1, Django’s built-in ``runserver`` is used
    to serve the GUI, and error pages are verbose.

    Don’t enable in production.


Environment variables read by Django
====================================

See ``docker-compose.yml``
container definitions, for example:

.. literalinclude:: /../docker-compose.yml
   :language: yaml
   :start-at: web:
   :end-before: depends_on:

Note ``SNAPSHOT_HASH`` and ``SNAPSHOT_TIME`` populated
using ``git``.
