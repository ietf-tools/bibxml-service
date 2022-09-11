=========
Evolution
=========

.. contents::
   :local:


Architecture
============

New API
-------

Existing integrations can be switched from xml2rfc-style paths to new API.
Using the new API endpoints (e.g., search)
service consumers should be able to achieve their goals with less logic,
and they can obtain the same XML.

After that, large part of :mod:`xml2rfc_compat` can be deprecated:
xml2rfc adapter registry and function implementations, URLs, xml2rfc mirror source.

Authentication
--------------

Instead of Basic HTTP auth, management GUI could potentially
use Datatracker OAuth2. (Datatracker API would need to provide
an endpoint to check whether given user has access to BibXML management.
After that, :func:`management.auth.basic` could be renamed appropriately
and use :func:`datatracker.oauth.get_client()` to make a request to that
endpoint. However, ideally Datatracker OAuth2 automatic token refresh should
be implemented first.)
