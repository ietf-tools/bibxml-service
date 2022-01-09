=================
Citation sourcing
=================

BibXML service deals with two types
of :term:`citation sources <citation source>`.

All citations indexed from internal/static sources can be searched,
while external citations can be retrieved individually by exact references
(incurring an extra server-to-server network request).

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

   - :func:`management.tasks._fetch_and_index`
   - :class:`main.models.RefData`

External sources
================

External sources don’t make citation data available
in bulk and in Relaton format.

- An external source allows to request an individual citation by document ID.
- It may or may not provide search across available citations.

Currently, only DOI (via Crossref API) is supported as external source.

.. seealso::

   - :func:`main.external.get_doi_ref`
