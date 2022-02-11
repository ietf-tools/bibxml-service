==============
Authentication
==============

.. contents::
   :local:

BibXML service uses multiple authentication mechanisms.

- Public service API requires authentication.

- Public GUI in general does not require authentication,
  but certain GUI features that require on API (such as bibliographic
  item export currently) may be omitted without authentication.

- Internal (management) GUI and POST API endpoints
  require authentication.

- Internal GET API endpoints do not require authentication.

Public-side auth
================

HTTP header token
-----------------

When accessing service API, a valid Datatracker developer’s token
(of “bibxml” type) can be passed in ``X-Datatracker-Token`` HTTP header.

For example::

    curl -sS \
      -Hcontent-type:application/json \
      -Hx-datatracker-token:<your_token> \
      -X GET \
      "<instance_url>/api/v1/by-docid/?docid=RFC8126"

In absence of ``X-Datatracker-Token``, API will try to validate
Datatracker OAuth access token, if found in current session,
and accept that as well.

.. seealso:: :mod:`datatracker.auth`

OAuth2/OpenID Connect
---------------------

Users can authenticate via Datatracker OAuth2/OpenID Connect,
after which access token is stored encrypted in user’s session.

.. seealso:: :mod:`datatracker.oauth`

Internal auth
=============

Internal authentication uses tokens provisioned at build or deploy time
via the ``API_SECRET`` and ``EXTRA_API_SECRETS`` environment variables,
and are used in ways described below.

Note: the service does not track activity per token API secret token.

.. seealso:: :mod:`management.auth`, :data:`bibxml.settings.API_SECRETS`

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

Applies to management GUI and Prometheus metrics endpoint.

- Username for Basic authentication is always
  :data:`bibxml.settings.API_USER`.

- Any of the ``API_SECRET`` tokens provided via the environment
  can be used as the password.
