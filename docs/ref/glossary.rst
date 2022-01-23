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
       and is a pair ``{ type, id }``, where ``type`` is :term:`document type`
       and determines the format of ``id``.

       The order of document identifiers matters.

       A single document can have multiple identifiers (e.g., a DOI, an ISBN, etc.).
       Each identifier is expected to be universally unique to this document.

       Multiple bibliographic items that share at least one document ID.
       are considered to be representing the same bibliographic item
       (see also :mod:`bib_models.merger`).

       .. note:: Not all identifier types are standardized at this time.

       .. todo:: Clarify whether bibliographic item with more than one document ID
                 of the same *type* is a logically valid scenario.

   docid.id
       Shorthand for the ``id`` component of :term:`document identifier`.

   document type
       The ``type`` component of :term:`document identifier`,
       contained in ``docid[*].type`` field of citation’s Relaton representation.

       Document type in Relaton is a somewhat murky concept.
       It is sometimes used to reference a namespace or registry
       (e.g., DOI, ISBN),
       and in other cases used to reference a publishing organization
       (e.g., IETF, IANA).

       Examples: ``IETF``, ``IEEE``, ``DOI``.

   bibliographic data source
       Where BibXML service obtains bibliographic items to show the user
       as a result of a query.

       - More than one source can provide data for the bibliographic items
         with the same :term:`document identifier`.
       - One source can provide bibliographic items of more than one document type.
       
       Citation source can be either an :term:`internal source`
       or an :term:`external source`.

   internal source
   indexed source
       Primary, fast to access source
       that returns bibliographic data in Relaton format
       with minimal or no processing and supports structured search.

       Itself is not an authoritative source and is ephemeral.
       During indexing stage it retrieves and pre-processes data
       from datasets (which are in turn compiled from authoritative sources).

       Currently there is only one internal source
       powered by PostgreSQL via Django ORM.

   dataset
       An external data source periodically compiled
       by Relaton-aware tools from authoritative sources.
       
       Currently delivered as a Git repository of certain structure
       with Relaton citation data serialized to YAML files.

       A dataset has to be indexed in order for the data to become
       available from the internal source.

   reference
   ref
       Name of an entry in a :term:`dataset`.
       Unique per dataset.

       - Not the same as :term:`document identifier`.
         Identifier can be considered part of public API,
         while reference is more an implementation detail of BibXML service.
       - If multiple references (typically from different datasets)
         contain the same ``{ type, id }`` combination in their data,
         those references are treated as representing
         the same :term:`bibliographic item`.

       References correspond to :class:`main.models.RefData` instances.

   external source
   external dataset
       Citation source that allows to retrieve individual bibliographic items
       given :term:`document identifier` (type and ID).
       Retrieval incurs a network request to external service
       and the cost of on-the-fly conversion to the requested format
       (Relaton or BibXML).

   indexing
       The process of retrieving bibliographic data from a :term:`dataset`
       and storing them in the database as :class:`main.models.RefData` instances.

       Involves cloning repositories and reading files therein.

   legacy dataset
       A set of manually crafted XML files that [used to be]
       provided by xml2rfc tools web server.

   legacy path
   xml2rfc-style path
       A path that used to be handled by xml2rfc tools web server.
       (Normally points to an XML file.)
