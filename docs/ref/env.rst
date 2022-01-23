==============================
Environment variable reference
==============================

Environment variables read by Django
====================================

The following variables are read from the environment
(either by Compose from shell where you execute ``docker compose``
or ``.env`` file, or by Django).

.. seealso:: :func:`main.bibxml.check_settings()`

``SNAPSHOT`` (**required**) (required by Django, provided by Compose)
    Version, taken from the latest Git tag.
    Obtained via `git describe --abbrev=0`.

``HOST`` (**required**) (required by Django and Compose, pass-through)
    Hostname used for Web GUI.
    HTTP requests with mismatching Host header will result in an error.

    Currently, it is used in ``ALLOWED_HOSTS`` setting,
    as well as Crossref etiquette.

``PORT`` (**required**) (required by Compose)
    Docker Compose will make Web GUI available
    on the host OS under this port number.

``CPU_COUNT`` (**recommended**) (required by Compose)
    Determines the number of workers in the web container.

``DB_NAME`` (**required**) (required by Django and Compose, pass-through)
    PostgreSQL database and user name.

``DB_USER`` (**required**) (provided by Compose)

``DB_HOST`` (**required**) (provided by Compose)

``DB_PORT`` (**required**) (provided by Compose)

``DB_SECRET`` (**required**) (required by Django and Compose, pass-through)
    User password for PostgreSQL server authentication.

``REDIS_HOST`` (**required**) (provided by Compose)

``REDIS_PORT`` (**required**) (provided by Compose)

``DJANGO_SECRET`` (**required**)  (required by Django and Compose, pass-through)
    Django’s secret key. Must be unique, long and confidential.

``API_SECRET`` (**required**) (required by Django and Compose, pass-through)
    Token for management GUI and API access.

``SERVICE_NAME`` (**required**) (required by Django and Compose, pass-through)
    The official name of the service. Short.

``CONTACT_EMAIL`` (**required**) (required by Django and Compose, pass-through)
    Email service operating team could be contacted via.
    May be used for exception notifications and more.

``SERVER_EMAIL`` (accepted by Django and Compose, pass-through)
    For emails sent by the service directly,
    this will be used as the “from” address.

``SENTRY_DSN`` (accepted by Django and Compose, pass-through)
    Endpoint for reporting metrics & errors to Sentry.

``DEBUG`` (accepted by Django and Compose, pass-through)
    If set to 1, Django’s built-in ``runserver`` is used
    to serve the GUI, and error pages are verbose.

    .. important:: Don’t set in production.

.. seealso:: :doc:`/howto/develop-locally` for sample development environment

.. seealso:: :doc:`/ref/containers`

Environment variables read by Django
====================================

See ``docker-compose.yml``
container definitions, for example:

.. literalinclude:: /../docker-compose.yml
   :language: yaml
   :start-at: web:
   :end-before: depends_on:
