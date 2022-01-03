=================
Citation sourcing
=================

BibXML service deals with two types of citation sources.

Internal (indexed) citations can be searched and explored,
while external citations can be retrieved individually by exact references
(incurring an extra server-to-server network request).

Internal sources
================

Citation sources maintained as Git repositories
with Relaton and BibXML citation data serialized into YAML/XML files
under ``data/`` within repository root.

- External tools periodically collect citations into these repositories.
- When BibXML service is instructed to retrieve citations
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

- BibXML service supports requesting individual citations from such a source.
- External sources are not searched.

Currently, only DOI (via Crossref API) is supported as external source.

.. seealso::

   - :func:`main.external.get_doi_ref`
