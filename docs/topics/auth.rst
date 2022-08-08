==============
Authentication
==============

.. contents::
   :local:

BibXML service uses multiple authentication mechanisms in different areas:

- Valid Datatracker developer’s token passed via ``X-Datatracker-Token`` HTTP header
- Datatracker OIDC/OAuth2 integration (valid access token in session)
- Basic HTTP auth
- An valid BibXML service API token passed via ``X-IETF-Token`` HTTP header

.. note::

   The project is not set up to use Django’s contrib user authentication.
   It may be worth introducing it later if warranted.

Public-side auth
================

By default, public service does *not* require any authentication.
However, this can be changed by setting :data:`bibxml.settings.REQUIRE_DATATRACKER_AUTH` to ``True``
(via runtime environment variable or by editing :mod:`bibxml.settings` source).

Below describes the behavior if :data:`bibxml.settings.REQUIRE_DATATRACKER_AUTH` is ``True``:

- Backward-compatible xml2rfc-style path API never requires authentication.

- All other public service API require authentication.

- Public GUI in general does not require authentication,
  but GUI features that rely on API (such as bibliographic
  item export links) are omitted if the user is not logged in via Datatracker
  (i.e., there’s no valid access token in user agent session).

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

- Internal (management) GUI and POST API endpoints
  require authentication.

- Internal GET API endpoints do not require authentication.

Internal authentication uses tokens provisioned at build or deploy time
via the ``API_SECRET`` and ``EXTRA_API_SECRETS`` environment variables,
and are used in ways described below.

.. note:: This service does not track activity per token API secret token.

.. important::

   All management view functions **must** be wrapped
   in :func:`management.auth.basic()` decorator.

   Management templates are passed API secret
   and include it to enable the user to trigger certain API endpoints
   (such as source reindexing) via client-side JS.

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
