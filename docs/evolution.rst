=========
Evolution
=========

.. contents::
   :local:


Architecture
============

Consolidating authentication
----------------------------

Instead of (admittedly, simple and probably sufficient) Basic HTTP auth,
management GUI could use Datatracker OAuth2.

Datatracker API would need to provide
an endpoint to check whether given user has access to BibXML management.
After that, :func:`management.auth.basic` could be renamed appropriately
and use :func:`datatracker.oauth.get_client()` to make a request to that
endpoint.

Concerns
~~~~~~~~

- Due to requirement uncertainty, Datatracker OAuth2 authentication
  for visitors can be turned on or off,
  and at the moment of writing is off.
  If it is not needed anymore, it might not be worth it to keep it
  only for management GUI, and instead maintain Basic HTTP
  and remove OAuth2 altogether.

- If OAuth2 is deemed useful but the optionality remains,
  the OAuth2 on/off switch
  :data:`bibxml.settings.REQUIRE_DATATRACKER_AUTH`
  may need to be renamed to clarify that it applies only to visitor GUI.

  - If warranted, it might be worth replacing that simple switch
    with a more complex setting
    dictating which authentication mechanisms are used for what
    or even a full access control implementation.


Requiring authentication to mitigate certain attacks
----------------------------------------------------

There is a tradeoff between search flexibility and performance.

High flexibility from being able to supply low-level JSON queries
means the service shifts part of the responsibility for not
abusing the system onto users, who can overload the database
with certain queries.

This could be mitigated by requiring authentication
for certain kinds of queries.


Obsoleting the :term:`xml2rfc-style path` API
---------------------------------------------

Existing integrations can be switched
from using :term:`xml2rfc-style paths <xml2rfc-style path>` to new API.
With new API providing endpoints without prior equivalents (e.g., search),
service consumers should be able to achieve their goals with less logic
while obtaining the same XML in the end.

After switching integrations, large parts of :mod:`xml2rfc_compat` can be deprecated
including xml2rfc adapter registry and function implementations, URLs,
:term:`xml2rfc archive source` implementation, possibly more.


Implementation
==============

Improvements that don’t radically changing how the service is organized.

Dockerfile
----------

- Use a newer Python 3.11 image.

  Should be possible when ``lxml`` has a wheel for 3.11,
  without it building from source significantly complicates Dockerfile
  and increases image size.


- Make images slimmer.

  It should be possible to improve performance by employing certain tactics
  that would result in smaller images that don’t include unused dependencies
  (e.g., Node for Celery, Git for web)

  See also :issue:`97`.
