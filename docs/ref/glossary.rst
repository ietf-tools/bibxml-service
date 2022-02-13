========
Glossary
========

.. glossary::

   document
       In context of BibXML, refers to a standard.

   bibliographic item
       Document metadata describing a document. Used when e.g. citing.
       Corresponds to ``BibliographicItem`` in Relaton models.

       In BibXML service, data for a single bibliographic item can be provided
       by multiple sources.

   citation
       In BibXML service codebase and documentation,
       sometimes mistakenly used as a synonym for :term:`bibliographic item`.

   docid
   document identifier
       Identifier of a document.

       May be given by publisher or issued by some third-party system.

       Contained in ``docid`` field of bibliographic item’s Relaton representation,
       and is a pair ``{ type, id, [primary] }``,
       where ``docid.type`` is :term:`document identifier type`
       and determines the format of :term:`docid.id`.

       A single document can have multiple identifiers (e.g., a DOI, an ISBN, etc.).
       Each identifier is expected to be universally unique to this document.

   primary document identifier
       :data:`bib_models.models.bibdata.DocID.primary` in Python.

       This service displays primary identifiers without identifier types,
       since types tend to be self-explanatory for them.

       The :term:`docid.id` value of a primary identifier ID
       uses format more or less similar to NIST’s PubID
       (possibly the only strongly standardized identifier format).
       It always starts with a prefix that denotes schema/document family.

   docid.id
       Shorthand for the ``id`` component of :term:`document identifier`.

   document identifier type
   docid.type
       The ``type`` component of :term:`document identifier`,
       contained in ``docid[*].type`` field of bibliographic item’s Relaton representation
       (:data:`bib_models.models.bibdata.DocID.type` in Python).

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
       
       Citation source can be either an :term:`indexable source`
       or an :term:`external source`.

   indexable source
       An external data source periodically compiled
       by Relaton-aware tools from authoritative sources.
       
       Currently delivered as a Git repository of certain structure
       with Relaton citation data serialized to YAML files.

       An indexable source has to be indexed in order for the data to become
       retrievable using this service.

       When user requests bibliographic data,
       this service returns items discovered across indexed sources first.

   indexed source
       An indexable source that has been indexed.

   reference
   ref
       Name of an entry in an :term:`indexed source`.
       Unique per dataset.

       Not the same as :term:`document identifier`.
       Document identifier is part of public API,
       while reference is more an implementation detail of BibXML service.

       References correspond to :class:`main.models.RefData` instances.

   external source
   external dataset
       Citation source that allows to retrieve individual bibliographic items
       given :term:`document identifier` (type and ID).
       Retrieval incurs a network request to external service
       and the cost of on-the-fly conversion to the requested format
       (Relaton or BibXML).

   indexing
       The process of retrieving bibliographic data from an :term:`indexable source`
       and storing them in the database as :class:`main.models.RefData` instances.

       Involves cloning repositories and reading files therein.

       See :mod:`management`.

   legacy dataset
       Sometimes used to refer to a set of manually crafted XML files that [used to be]
       provided by xml2rfc tools web server.

   legacy path
   xml2rfc-style path
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
      a :class:`bib_models.models.bibdata.BibliographicItem` instance,
      and is expected to raise either :class:`sources.exceptions.RefNotFoundError`
      or :class:`pydantic.ValidationError`.

      .. seealso:: :ref:`xml2rfc-path-resolution-algorithm`
