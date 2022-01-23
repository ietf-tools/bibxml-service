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

``HOST`` (**required**)
    Hostname used for Web GUI.
    HTTP requests with mismatching Host header will result in an error.

    Currently, it is used in ``ALLOWED_HOSTS`` setting,
    but planned to be reused in other places as well.
    Thus, a wildcard *is not allowed*.

``PORT`` (**required**)
    Docker Compose will make Web GUI available
    on the host OS under this port number.

``CPU_COUNT`` (**recommended**)
    Determines the number of workers in the web container.

``DB_NAME`` (**required**)
    PostgreSQL database and user name.

``DB_SECRET`` (**required**)
    User password for PostgreSQL server authentication.

``DJANGO_SECRET`` (**required**)
    Django’s secret key. Must be unique, long and confidential.

``API_SECRET`` (**required**)
    Token for management GUI and API access.

``SERVICE_NAME`` (**required**)
    The official name of the service. Short.

``CONTACT_EMAIL`` (**required**)
    Email service operating team could be contacted via.
    May be used for exception notifications and more.

``SERVER_EMAIL``
    For emails sent by the service directly,
    this will be used as the “from” address.

``SENTRY_DSN``
    Endpoint for reporting metrics & errors to Sentry.

``DEBUG``
    If set to 1, Django’s built-in ``runserver`` is used
    to serve the GUI, and error pages are verbose.

    .. important:: Don’t set in production.


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
