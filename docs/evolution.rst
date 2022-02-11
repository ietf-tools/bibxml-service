=========
Evolution
=========

We believe the service can evolve in following ways:

1. Existing integrations can be switched from xml2rfc-style paths to new API.
   After that, large part of :mod:`xml2rfc_compat` can be deprecated:
   fetcher registry and function implementations, URLs, xml2rfc mirror source.

2. Instead of Basic HTTP auth, management GUI could potentially
   use Datatracker OAuth2. (Datatracker API would need to provide
   an endpoint to check whether given user has access to BibXML management.
   After that, :func:`management.auth.basic` could be renamed appropriately
   and use :func:`datatracker.oauth.get_client()` to make a request to that
   endpoint. However, ideally Datatracker OAuth2 automatic token refresh should
   be implemented first.)
