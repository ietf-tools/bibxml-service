===========================
xml2rfc tools compatibility
===========================

.. contents::
   :local:

Pre-existing :term:`xml2rfc paths <xml2rfc-style path>`
are maintained in the following way.

.. seealso:: If you have cases where paths are resolved incorrectly,
             :doc:`/howto/adjust-xml2rfc-paths`.

.. _xml2rfc-path-resolution-algorithm:

xml2rfc-style path resolution algorithm
=======================================

Root URL configuration includes xml2rfc-style paths via 
:func:`xml2rfc_compat.urls.get_urls()`.
Each path is handled the following way:

1. A manual mapping is looked up for requested path.
   If found, bibliographic item with mapped docid
   is attempted to be retrieved and returned as XML.
   
2. If the above fails, the path is passed to registered fetcher function,
   which parses the anchor, performs necessary DB queries and is expected
   to return a ``BibliographicItem``.
   
3. If no bibliographic item can be located, URL handler falls back
   to pre-indexed xml2rfc web server data.

.. note::

   Only a path for which an :term:`xml2rfc fetcher` is registered will be handled,
   even though that fetcher function is not necessarily called.

.. seealso:: :func:`xml2rfc_compat.urls.make_xml2rfc_path_pattern()`

Manual mapping
--------------

Manual maps are stored in the DB as :class:`xml2rfc_compat.models.ManualPathMap`
instances. The management GUI provides an utility for managing these mappings.

A map associates given xml2rfc path with a :term:`docid.id`.
When that path is requested, this service looks up that identifier
in :term:`bibliographic data sources <bibliographic data source>`.

.. seealso:: :func:`xml2rfc_compat.urls.resolve_manual_map()`

Fetcher functions
-----------------

:term:`Fetcher functions <xml2rfc fetcher>` are associated with subdirectories
(e.g., ``bibxml9``) via :func:`xml2rfc_compat.urls.register_fetcher`.

Fetcher functions are currently defined in :mod:`xml2rfc_compat.fetchers`.

.. seealso:: :func:`xml2rfc_compat.urls.resolve_automatically()`

Fallback
--------

If manual map is not present or failed, and fetcher function failed,
fallback document is attempted to be used.

Fallback data is provided via :mod:`xml2rfc source <xml2rfc_compat.source>`,
*which has to be indexed* in order for fallback to work.
The source consumer the hard-coded xml2rfc mirror Git repository,
storing path and associated XML data in the DB without further validation.

The ``anchor`` property in obtained fallback XML
is replaced with effective anchor at during request.

.. seealso:: :func:`xml2rfc_compat.urls.obtain_fallback_xml()`

Tracked metrics
===============

:data:`prometheus.metrics.xml2rfc_api_bibitem_hits`
    incremented on each request (unless X-Requested-With header is xml2rfcResolver:
    this is used by xml2rfc path resolutoion management tool to avoid
    skewing the metric).
    The ``outcome`` label reports 'success', 'not_found_fallback' if fallback was required,
    or 'not_found_no_fallback' if fallback failed.
