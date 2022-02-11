==============
Authentication
==============

.. contents::
   :local:

BibXML service uses multiple authentication mechanisms.

Datatracker-based auth
======================

HTTP header token
-----------------

Applies to bibliographic data retrieval APIs.

A valid Datatracker developer’s token (of “bibxml” type)
is expected to be passed in ``X-Datatracker-Token`` HTTP header.
For example::

    curl -sS \
      -Hcontent-type:application/json \
      -Hx-datatracker-token:<your_token> \
      -X GET \
      "<instance_url>/api/v1/by-docid/?docid=RFC8126"

.. seealso:: :mod:`datatracker.auth`

OpenID Connect
--------------

Users can authenticate with Datatracker
via OAuth2/OpenID Connect.

.. seealso:: :mod:`datatracker.oauth`

Internal auth
=============

Internal authentication uses tokens provisioned at build or deploy time
via the ``API_SECRET`` and ``EXTRA_API_SECRETS`` environment variables,
and are used in ways described below.

Note: the service does not track activity per token API secret token.

.. seealso:: :mod:`management.auth`

HTTP header token
-----------------

Applies to management API POST endpoints (see OpenAPI spec).

One of API secret tokens provisioned at deploy time
is expected to be passed in ``X-IETF-Token`` HTTP header.
For example::

    curl -i \
      -X POST \
      -H "X-IETF-token: <your_token>" \
      "<instance_url>/api/v1/management/misc/reindex/"

Basic HTTP auth
---------------

Applies to management GUI endpoints and Prometheus metrics endpoint.

Username for Basic authentication is always ``ietf``,
and any of the tokens provided via the environment can be used
as the password.
