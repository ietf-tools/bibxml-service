===========================
xml2rfc tools compatibility
===========================

.. contents::
   :local:

xml2rfc tool compatibility aims to:

- Offer XML output in line with RFC 7991
  (with bias towards preexisting xml2rfc tools web server output,
  where it differs from the RFC) in API.

- Handle pre-existing :term:`paths <xml2rfc-style path>`
  provided by xml2rfc tools web server by providing
  up-to-date bibliographic data in the abovementioned XML format
  when possible.

- Provide xml2rfc path for bibliographic item in service GUI
  (per :issue:`225`).

.. seealso::

   - :rfp:req:`5`

   - :term:`BibXML foramt`

   - If you have cases where paths are resolved incorrectly,
     :doc:`/howto/adjust-xml2rfc-paths`.

   - :mod:`xml2rfc_compat` for Python module reference

BibXML format support
=====================

Output format support is implemented via :mod:`~xml2rfc_compat.serializer`.

.. _xml2rfc-path-resolution-algorithm:

xml2rfc-style path resolution algorithm
=======================================

1. Requested path is normalized: for example,
   this removes the underscore preceding ``reference``
   in ``public/rfc/bibxml/_reference.foo.bar.xml``, adjusting it
   to ``public/rfc/bibxml/reference.foo.bar.xml``.

2. A :term:`docid` mapping is looked up for the normalized path.
   If found, bibliographic item with mapped docid
   is attempted to be retrieved from authoritative sources
   and its XML serialization is returned.

3. If the above fails, registered adapter is used
   to attempt to obtain a bibliographic item
   from authoritative sources
   based on dirname and anchor in requested path.

4. If no bibliographic item can be located, attempt to obtain
   fallback XML for given path from :term:`xml2rfc archive source`
   as last resort, and return that.

.. note::

   GET query parameter ``anchor``,
   if given, replaces top-level reference anchor in XML
   (even fallback XML).

.. note:: If no :term:`xml2rfc adapter` is registered for given path,
          this process does not take place.

.. seealso::

   Root URL configuration includes xml2rfc-style paths via
   :func:`xml2rfc_compat.urls.get_urls()`, and xml2rfc path handling
   is done by :func:`xml2rfc_compat.views.handle_xml2rfc_path`.

Mapping
-------

A map associates given xml2rfc path with a :term:`primary document identifier`.
When that path is requested, this service looks up that identifier
in :term:`bibliographic data sources <bibliographic data source>`.

Mappings are obtained from
:term:`xml2rfc sidecar metadata files <xml2rfc sidecar metadata file>`,
provided within the :term:`xml2rfc archive source`
and named after the preexisting XML files in it.

During indexing, this data is stored in DB
as part of the relevant :class:`xml2rfc_compat.models.Xml2rfcItem`
instance.

The management GUI may provide a utility for exploring manual mappings.

.. seealso:: :func:`xml2rfc_compat.views.resolve_mapping()`

Adapter
-----------------

:term:`Adapters <xml2rfc adapter>` are associated with subdirectories
(e.g., ``bibxml9``) via :func:`xml2rfc_compat.adapters.register_adapter`.

Concrete adapters can be found in :mod:`bibxml.xml2rfc_adapters`.
This module must be imported at service startup to ensure registration is done.

.. seealso:: :func:`xml2rfc_compat.views.resolve_automatically()`

Fallback
--------

If manual map is not present or failed, and adapters failed,
fallback XML string is attempted to be used.

Fallback data is provided via the :term:`xml2rfc archive source`,
*which has to be indexed* in order for fallback to work.
The source consumer the hard-coded xml2rfc mirror Git repository,
storing path and associated XML data in the DB without further validation.

The ``anchor`` property in obtained fallback XML
is replaced with effective anchor at during request.

.. seealso:: :func:`xml2rfc_compat.views.obtain_fallback_xml()`

Tracked metrics
---------------

:data:`prometheus.metrics.xml2rfc_api_bibitem_hits`
    incremented on each request (unless X-Requested-With header is xml2rfcResolver:
    this is used by xml2rfc path resolutoion management tool to avoid
    skewing the metric).
    The ``outcome`` label reports 'success', 'not_found_fallback' if fallback was required,
    or 'not_found_no_fallback' if fallback failed.
