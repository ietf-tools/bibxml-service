========
Glossary
========

.. glossary::

   bibliographic item
       Document metadata describing a document. Used when e.g. citing.
       Corresponds to :class:`bib_models.models.bibdata.BibliographicItem` instance.

       In BibXML service, data for a single bibliographic item can be provided
       by multiple sources.

   citation
       In BibXML service codebase and documentation,
       sometimes mistakenly used as a synonym for :term:`bibliographic item`.

   docid
   document identifier
       Identifier of a document.

       A document can have multiple identifiers (e.g., a DOI, an ISBN, etc.),
       and sometimes a single identifier can be shared by multiple documents
       (however, such an ambiguous identifier
       should not be :term:`primary <primary document identifier>`,
       or it should be reported as a data integrity issue).

       Identifiers are listed
       under :data:`BibliographicItem.docid <bib_models.models.bibdata.BibliographicItem.docid>`,
       and each identifier is a :class:`bib_models.models.bibdata.DocID` instance in Python.

   primary document identifier
       Main characteristics of a primary identifier:

       - Its ``id`` can be used to unambiguously reference the document.
       - A primary identifier is expected to be
         universally unique to this document.

       This service displays primary identifiers without identifier types,
       as types tend to be self-explanatory.

       The :data:`~bib_models.models.bibdata.DocID.id` value of a primary identifier
       uses format more or less similar to NIST’s PubID
       (possibly the only strongly standardized identifier format).
       It always starts with a prefix that denotes schema/document family.

       In Python, such identifiers have their :data:`~bib_models.models.bibdata.DocID.primary`
       attribute set to ``True``.

   docid.id
       Refers to :data:`bib_models.models.bibdata.DocID.id`.

   document identifier type
   docid.type
       The ``type`` component of :term:`document identifier`,
       contained in ``docid[*].type`` field of bibliographic item’s Relaton representation
       (field :data:`~bib_models.models.bibdata.DocID.type` in Python).

       Document identifier type in Relaton is a somewhat murky concept.
       In case of a :term:`primary document identifier`, its type tends to be used
       to reference a namespace or registry
       (e.g., DOI, ISBN),
       and in other cases used to reference a publishing organization
       (e.g., IETF, IANA).

       Examples: ``IETF``, ``IEEE``, ``DOI``.

   bibliographic data source
   dataset
       Where BibXML service obtains bibliographic items to show the user
       as a result of a query.

       - More than one source can provide data for the bibliographic items
         with the same :term:`document identifier`.
       - One source can provide bibliographic items of more than one document type.
       
       Bibliographic data can come from an :term:`indexable source`
       or an :term:`external source`.

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

   xml2rfc-style path
   legacy path
       A path that used to be handled by xml2rfc tools web server.
       (Normally points to an XML file.)

       See :doc:`/topics/xml2rfc-compat` and :data:`xml2rfc_compat.models.dir_subpath_regex`.

   xml2rfc anchor
      Part of the filename in an :term:`xml2rfc-style path`
      without “reference” or “_reference” prefix and file extension.

      It also appears as the “anchor” attribute on the ``<reference>``
      element in returned XML.

   xml2rfc fetcher function
   xml2rfc fetcher
      A function registered and associated with a top-level xml2rfc subpath
      via :func:`xml2rfc_compat.urls.register_fetcher`.

      Fetcher function is passed the ``anchor`` argument as a string,
      for which it must return
      a :class:`~bib_models.models.bibdata.BibliographicItem` instance,
      and is expected to raise either :class:`sources.exceptions.RefNotFoundError`
      or :class:`pydantic.ValidationError`.

      .. seealso:: :ref:`xml2rfc-path-resolution-algorithm`
