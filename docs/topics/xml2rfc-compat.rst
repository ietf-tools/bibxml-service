===================================
xml2rfc tools web API compatibility
===================================

Pre-existing :term:`xml2rfc paths <xml2rfc-style path>`
are maintained in the following way:

1. Fetcher functions are defined in :mod:`xml2rfc_compat.fetchers`.
   Each fetcher function accepts an anchor,
   which would be an xml2rfc filename base (a.k.a. anchor),
   and returns a :class:`bib_models.models.BibliographicItem` instance.

2. Fetcher functions are associated with subdirectories
   (e.g., ``bibxml9``) via :func:`xml2rfc_compat.urls.make_xml2rfc_path_pattern`,
   which returns a ``re_path()`` suitable for plugging into URL configuration.

Resolution
==========

Each incoming request is passed to a fetcher function,
which parses anchor, performs necessary DB queries and is expected
to return a ``BibliographicItem``.

If no bibliographic item can be located, handler falls back
to pre-indexed xml2rfc web server data.

.. seealso:: If you have cases where fetcher cannot locate a bib item,
             :doc:`/howto/adjust-xml2rfc-paths`.

Tracked metrics
===============

:data:`prometheus.metrics.xml2rfc_api_bibitem_hits`
    incremented on each request. The ``outcome`` label
    reports 'success', 'not_found_fallback' if fallback was required,
    or 'not_found_no_fallback' if fallback failed.
