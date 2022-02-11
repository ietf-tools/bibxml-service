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
       and is a pair ``{ type, id }``,
       where ``docid.type`` is :term:`document identifier type`
       and determines the format of :term:`docid.id`.

       A single document can have multiple identifiers (e.g., a DOI, an ISBN, etc.).
       Each identifier is expected to be universally unique to this document.

   primary document identifier
       An identifier the ``id`` of which is used when citing/linking to document.

       Such an identifier is shown without its identifier type.

       DOI, ISBN are *not* primary identifiers.

   docid.id
       Shorthand for the ``id`` component of :term:`document identifier`.

   document identifier type
   docid.type
       The ``type`` component of :term:`document identifier`,
       contained in ``docid[*].type`` field of citation’s Relaton representation.

       Document identifier type in Relaton is a somewhat murky concept.
       In case of a “primary” identifier, type tends to be used
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

       See :doc:`/topics/xml2rfc-compat`.
