===========================
Bibliographic data sourcing
===========================

BibXML service deals with two types
of :term:`bibliographic data sources <bibliographic data source>`.

Internal sources
================

Internal sources are under IETF control,
and are maintained as Git repositories
with Relaton and BibXML citation data serialized into YAML/XML files
under ``data/`` within repository root.

These sources are periodically updated by tools outside of BibXML service.

When BibXML service is instructed to retrieve citations
from any of those sources, it queues an asynchronous task
that pulls or clones the relevant repositories,
reads citation data and populates the database,
making citations searchable over API and GUI.

.. seealso::

   - :func:`sources.tasks.fetch_and_index_task`
   - :class:`main.models.RefData`

External sources
================

External sources don’t make citation data available
in bulk and in Relaton format.

- An external source allows to request an individual citation by document ID.
- It may or may not provide search across available citations.

Currently, only DOI (via Crossref API) is supported as external source,
and source registration does not support external sources.

.. seealso::

   - :func:`doi.get_doi_ref`
