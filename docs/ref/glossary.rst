========
Glossary
========

.. glossary::

   document
       In context of BibXML, this refers to a standard.

   citation
   bibliographic item
       Document metadata used to reference a document when citing.
       Corresponds to ``BibliographicItem`` in Relaton models.

       In BibXML service, data for a single citation can be provided
       by multiple datasets.

       For indexed citations, data for a citation with particular :term:`docid`
       is created from ``body`` values on ``RefData`` instance(s) that specify
       that docid.

   docid
   document identifier
       Identifier given to the document by the publisher and/or author.

       Contained in ``docid`` field of citation’s Relaton representation,
       and is a pair ``{ type, id }``, where ``type`` is :term:`document type`
       and determines the format of ``id``.

       A single document can have multiple identifiers (e.g., a DOI, an ISBN, etc.).
       Each identifier is expected to be universally unique to this document.

       .. note:: Not all identifier formats are standardized at this time.

       .. todo:: Clarify whether citation with more than one ID of the same *type*
                 is a logically valid scenario.

   document type
       Part of :term:`document identifier` representing the family of documents.
       Often but not always the same as publishing organization’s abbreviation.

       Contained in ``docid[*].type`` field of citation’s Relaton representation.

       Examples: ``IETF``, ``IEEE``.

   dataset
   citation source
       Source of citation data.

       There is no 1:1 relationship between dataset and :term:`document type`.

       - One dataset can provide citations of more than one document type.
       - More than one dataset can provide data for the citation
         with the same :term:`document identifier`.
       
       Citation source can be either a :term:`Relaton source`
       or an :term:`external source`.

   reference
   ref
       Name of an entry in a static dataset.
       Unique per dataset.

       - Not the same as :term:`document identifier`.
         Identifier can be considered part of public API,
         while reference is more an implementation detail of BibXML service.
       - If multiple references (typically from different datasets)
         contain the same ``{ type, id }`` combination in their data,
         those references are treated as representing the same :term:`citation`.

       Indexed references correspond to :class:`main.models.RefData` instances.

   static dataset
   Relaton source
       Citation source that allows to retrieve all of its citations in bulk
       in Relaton format with minimal or no processing.

       The typical mechanism is a Git repository
       with Relaton citation data serialized to YAML files.

   external dataset
   external source
       Citation source that allows to retrieve individual citations
       given :term:`document identifier` (type and ID).
       Retrieval incurs a network request to external service
       and the cost of on-the-fly conversion to the requested format
       (Relaton or BibXML).

   indexing
       The process of retrieving citations from a static dataset
       and storing them in the database as :class:`main.models.RefData` instances.

   legacy dataset
       A set of manually crafted XML files that [used to be]
       provided by xml2rfc tools web server.

   legacy path
       A path that used to be handled by xml2rfc tools web server.
       (Normally points to an XML file.)
