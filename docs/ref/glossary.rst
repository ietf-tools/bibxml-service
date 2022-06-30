========
Glossary
========

.. seealso:: :doc:`relaton:glossary` in ``relaton-py`` library documentation

.. glossary::

   bibliographic data source
   dataset
       Where BibXML service obtains bibliographic items to show the user
       as a result of a query.

       - More than one source can provide data for the bibliographic items
         with the same :term:`document identifier`.
       - One source can provide bibliographic items of more than one document type.

       Can either be an :term:`indexable source` or an :term:`external source`.

   BibXML format
       XML using schema defined
       by `RFC 7991 <https://datatracker.ietf.org/doc/html/rfc7991>`_
       or newer `Xml2rfc vocabulary <https://xml2rfc.tools.ietf.org/xml2rfc-doc.html>`_.

   indexable source
       An external data source periodically compiled by external tools
       from authoritative source(s).
       Has to be indexed in order for the data to become
       retrievable using this service.

       An indexable source must be registered and associated with
       the function that handles the indexing via
       :func:`sources.indexable.register_git_source()`.
       After that, it appears in management GUI and API
       and its indexing can be queued.

       Currently, an indexable source must be a Git repository.

       Examples: Relaton sources registered in :mod:`main.sources`;
       xml2rfc mirror data source registered in :mod:`xml2rfc_compat.source`.

   indexed source
       An :term:`indexable source` that has been indexed.

   reference
   ref
       Name of an entry in an :term:`indexed source`.
       Unique per source.

       In case of Relaton sources, references
       correspond to :class:`main.models.RefData` instances.

       .. note:: Being a dataset-specific reference (such as a filename),
                 it is not expected to be known by the user. Hence, user searches
                 should not use :term:`ref`, but instead use
                 a :term:`document identifier`.

       .. seealso::

          :func:`main.query.get_indexed_item` retrieves a bibliographic item
          matching given source and source-specific reference, if it is indexed.

   external source
   external dataset
       A :term:`bibliographic data source`
       that allows to retrieve individual bibliographic items
       given :term:`document identifier`.
       Retrieval incurs a network request to external service
       and the cost of on-the-fly conversion to Relaton and optionally requested
       serialization format.

       Example: Crossref is an external source that allows to look up
       bibliographic items via DOI (see :mod:`doi`).

       Register external sources using
       :func:`main.external_sources.register_for_types()`.

   xml2rfc-style path
   legacy path
       A path that used to be handled by xml2rfc tools web server.
       (Normally points to an XML file.)

       .. seealso::

          - :rfp:req:`5` for background
          - :doc:`/topics/xml2rfc-compat` for overview
          - :data:`xml2rfc_compat.models.dir_subpath_regex` for the regular expression

   xml2rfc archive source
   xml2rfc mirror source
      An :term:`indexable source` (living in a Git repository)
      that contains two kinds of data:

      - Original XML files as served by xml2rfc tools web server.

        These files are supposed to be periodically overwritten using rsync
        from rsync mirror.

      - :term:`Optional “sidecar” YAML files <xml2rfc sidecar metadata file>`.

      .. seealso:: :mod:`xml2rfc_compat.source`

   xml2rfc sidecar metadata file
      A YAML file named after an XML file existing in :term:`xml2rfc archive source`,
      describing e.g. which bibliographic item it maps to.

      Among other things, it can describe which :term:`document identifier`
      the relevant XML file maps to, in order for the service to prefer an up-to-date
      document if it exists
      among available indexed :term:`bibliographic data sources <bibliographic data source>`.

      These YAML files can be edited using external tooling or by hand,
      and are not overwritten when xml2rfc archive source is automatically updated.

      .. seealso::

         - :attr:`xml2rfc_compat.models.Xml2rfcItem.sidecar_meta`
         - :class:`xml2rfc_compat.types.Xml2rfcPathMetadata`

   xml2rfc anchor
      Part of the filename in an :term:`xml2rfc-style path`
      without “reference” or “_reference” prefix and file extension.

      It also appears as the “anchor” attribute on the ``<reference>``
      element in returned XML.

   xml2rfc fetcher function
   xml2rfc fetcher
      A function registered and associated with a top-level xml2rfc subpath
      via :func:`xml2rfc_compat.resolvers.register_fetcher`.

      Fetcher function is passed the ``anchor`` argument as a string,
      for which it must return
      a :class:`~relaton.models.bibdata.BibliographicItem` instance,
      and is expected to raise either :class:`main.exceptions.RefNotFoundError`
      or :class:`pydantic.ValidationError`.

      .. seealso:: :ref:`xml2rfc-path-resolution-algorithm`

   anchor formatter function
      A function that can be optionally registered for a top-level xml2rfc subpath
      via :func:`xml2rfc_compat.resolvers.register_anchor_formatter`.

      If provided for given xml2rfc directory, it will be called when formatting
      the anchor attribute in resulting XML.

      (Has no effect if an anchor is given in GET query.)
