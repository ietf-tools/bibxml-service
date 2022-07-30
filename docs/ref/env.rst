==============================
Environment variable reference
==============================

.. contents::
   :local:

Environment variables read by web application
=============================================

The following variables are read from the environment
(either by Compose from shell where you execute ``docker compose``
or ``.env`` file, or by web application).

Variables marked as required or accepted by Django
are generally assigned to a member of :mod:`bibxml.settings`,
they can either influence a Django’s own setting
or service’s custom setting.

.. seealso:: :func:`bibxml.env_checker.env_checker()`

.. seealso::

   - :doc:`/howto/develop-locally` for sample development environment
   - :doc:`/howto/run-in-production` for sample production environment


Service info
------------

``SERVICE_NAME``
    **required by Django** and Compose, pass-through

    The official name of the service. Short.

``CONTACT_EMAIL``
    **required by Django** and Compose, pass-through

    Email service operating team could be contacted via.
    May be used for exception notifications and more.

``SNAPSHOT``
    **required by Django**, provided by Compose, works as a Docker build arg.

    Version, taken from the latest Git tag.
    Can be obtained via `git describe --abbrev=0`.

    .. note:: In CI like GHA, repositories are cloned without history
              by default, in which case the above command will not
              return the latest tag. Possible workarounds:

              - Change clone behavior to full. This will make it slower.
              - Use another method of obtaining the latest tag.

                In case of GHA, the ``GITHUB_REF`` environment variable
                provides the pushed ref.
                You can set ``on: { push: { tags: ['*'] } }`` in your workflow,
                meaning builds only happen on pushed tags and ``GITHUB_REF``
                can be relied on to have tag name in it.
                It can be extracted with something like
                ``SNAPSHOT="${GITHUB_REF#refs/*/}"``.

``SOURCE_REPO_URL``
    accepted by Django and Compose, pass-through, recommended in production

    If provided, some pages of the service will show visitors a link
    to this source repository.

``SERVER_EMAIL``
    accepted by Django and Compose, pass-through, recommended in production

    For emails sent by the service directly,
    this will be used as the “from” address.


Web server
----------

``PRIMARY_HOSTNAME``
    **required by Django** and (as ``HOST``) by Compose

    Hostname used for Web GUI.
    HTTP requests with mismatching Host header will result in an error.

    Currently, it is used in ``ALLOWED_HOSTS`` setting,
    as well as Crossref etiquette.

``INTERNAL_HOSTNAMES``
    accepted by Django and Compose, pass-through

    Alternative hostnames which could be used by internal services
    (e.g., in Compose configuration Prometheus refers to web container
    by its Compose hostname, so Django needs to recognize it).

``PORT``
    required by Compose

    Docker Compose will make Web GUI available
    on the host OS under this port number.

``RESPOND_TO_DETECTED_INTERNAL_HOSTNAME``
    accepted by Django

    If set to 1, Django will machine’s hostname detected at runtime
    to the list of ``INTERNAL_HOSTNAMES``.

``RESPOND_TO_DETECTED_INTERNAL_IPS``
    accepted by Django

    If set to 1, Django will machine’s IPs detected at runtime
    to the list of ``INTERNAL_HOSTNAMES``.

    .. note:: This only supports IPv4 at this time.


Main database
-------------

``DB_NAME``
    **required by Django** and Compose, pass-through

    PostgreSQL database and user name.

``DB_USER``
    **required by Django**, provided by Compose from ``DB_NAME``

    Username for PostgreSQL server authentication.

``DB_HOST``
    **required by Django**, provided by Compose

    DB server hostname.

``DB_PORT``
    **required by Django**, provided by Compose

    DB server port number.

``DB_SECRET``
    **required by Django** and Compose, pass-through

    User password for PostgreSQL server authentication.


.. _indexing-env-variables:

Indexing
--------

``DATASET_TMP_ROOT``
    accepted by Django

    Which directory to store fetched sources when indexing.
    Must be an absolute path.

    See :data:`bibxml.settings.DATASET_TMP_ROOT`.

``AUTO_REINDEX_INTERVAL``
    accepted by Django and Compose, pass-through

    How many seconds to wait before reindexing a source.
    Must be larger than zero for reindexing to be enabled.

    See :data:`bibxml.settings.AUTO_REINDEX_INTERVAL` for more.


Celery & Redis
--------------

``REDIS_HOST``
    **required by Django**, provided by Compose

``REDIS_PORT``
    **required by Django**, provided by Compose

``CELERY_BROKER_URL``
    **required by Django**, provided by Compose

    Point this to Redis host & port.

``CELERY_RESULT_BACKEND``
    **required by Django**, provided by Compose

    Point this to Redis host & port.


Security
--------

``DJANGO_SECRET``
    **required by Django** and Compose, pass-through

    Django’s secret key. Must be unique, long and confidential.

``API_SECRET``
    **required by Django** and Compose, pass-through

    Token for management GUI and API access,
    as well as Prometheus metrics endpoint access.

    .. seealso:: :doc:`/topics/auth`

    Compose also uses it as admin password with Grafana container
    (username is “ietf”).

``EXTRA_API_SECRETS``
    accepted by Django and Compose, pass-through

    Extra tokens, as a single comma-separated string.

    Each will have the same effect and access privileges
    as ``API_SECRET``.

``DEBUG``
    accepted by Django and Compose, pass-through

    If set to 1, Django’s built-in ``runserver`` is used
    to serve the GUI, and error pages are verbose.

    It will also try to auto-detect IPs and hostnames and add them
    to ``INTERNAL_IP`` for Django debug toolbar to work
    in Docker environment.

    .. important:: Don’t set in production.


Integrations
------------

Sentry
~~~~~~

``SENTRY_DSN``
    accepted by Django and Compose, pass-through

    Endpoint for reporting metrics & errors to Sentry.


.. _datatracker-integration-env:

Datatracker
~~~~~~~~~~~

All of these are required for Datatracker OAuth2 login to work.

.. seealso:: :mod:`datatracker.oauth`

``DATATRACKER_CLIENT_ID``
    accepted by Django and Compose, pass-through

``DATATRACKER_CLIENT_SECRET``
    accepted by Django and Compose, pass-through

``DATATRACKER_REDIRECT_URI``
    accepted by Django

    Indicates the redirect URI configured for given client ID/secret
    on Datatracker side.
    The application will check if internal URL pattern configuration
    yields the same URI, and consider Datatracker OAuth misconfigured if not.


.. _matomo-integration-env:

Matomo
~~~~~~

``MATOMO_URL``
    accepted by Django and Compose, pass-through

``MATOMO_SITE_ID``
    accepted by Django and Compose, pass-through

``MATOMO_TAG_MANAGER_CONTAINER``
    accepted by Django and Compose, pass-through

.. seealso::

   The :data:`~bibxml.settings.MATOMO` setting for more details.

   Matomo’s own resources:

   - `Matomo tracker integration <https://developer.matomo.org/guides/tracking-javascript-guide>`_
   - `MTM integration <https://developer.matomo.org/guides/tagmanager/embedding>`_

   :github:`static/js/matomo.js` and :github:`templates/base.html`.


Environment variables passed through by Docker Compose
======================================================

See ``docker-compose.yml``
container definitions, for example:

.. literalinclude:: /../docker-compose.yml
   :language: yaml
   :start-at: web:
   :end-before: depends_on:
