========
Glossary
=======

.. glossary::

   document
       Generally, this refers to a standard.

   citation
       Document metadata used to reference a document when citing.
       Corresponds to ``BibliographicItem`` in Relaton models.

       In BibXML service, data for a single citation can be provided
       by multiple datasets.

   document identifier
   docid
       Contained in ``docid`` field of citation’s Relaton representation
       as a pair ``{ type, id }``, where ``type`` is :term:`document type`
       and determines the format of ``id``.

       A single citation can have multiple IDs (e.g., a DOI, an ISBN, etc.).

       - It is unclear whether multiple IDs of the same *type* is logically valid.

   document type
       Represents a family of documents.
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

   reference
   ref
       Name of an entry in a static dataset.
       Unique per dataset.

       - Not the same as :term:`document identifier`.
       - If multiple references (typically from different datasets)
         contain the same ``{ type, id }`` combination in their data,
         those references are treated as representing the same :term:`citation`.

       Indexed references correspond to :class:`main.models.RefData` instances.

   static dataset
   internal dataset
       Citation source that allows to retrieve all of its citations in bulk
       in Relaton format with minimal or no processing.

       The typical mechanism is a Git repository
       with Relaton citation data serialized to YAML files.

   external dataset
       Citation source that allows to retrieve a single citation
       given document type and ID. Retrieval incurs a network request
       and the cost of on-the-fly conversion to requested format
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
