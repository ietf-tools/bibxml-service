===========================
Bibliographic data sourcing
===========================

BibXML service deals with two types
of :term:`bibliographic data sources <bibliographic data source>`.

Internal sources
================

Internal sources are under IETF control,
and are maintained as Git repositories
with Relaton and BibXML bibliographic data serialized into YAML/XML files
under ``data/`` within repository root.
They are periodically updated by tools outside of BibXML service.

These repositories are registered as :term:`indexable sources <indexable source>`.
(When BibXML service is instructed to reindex any indexable source,
it queues an asynchronous task
that pulls or clones the relevant repositories and runs specified indexer function
that reads the data and populates the database.)

The full list of internal sources is provided in :data:`bibxml.settings.RELATON_DATASETS`.
For every item in that list, a repository URL can be obtained
using the apptoach in :func:`main.sources.locate_relaton_source_repo()`: the common case
is ``https://github.com/ietf-ribose/relaton-data-{dataset ID}`` with branch name ``main``
(where “dataset ID” is the string from ``RELATON_DATASETS``),
unless an override is specified in :data:`bibxml.settings.DATASET_SOURCE_OVERRIDES`
for that dataset ID (in which case that setting will have ``relaton_data.repo_url``
specifying URL and/or branch name explicitly).

.. seealso::

   - :mod:`main.sources`

External sources
================

External sources don’t make bibliographic data available
in bulk in Relaton format.

.. seealso::

   - :func:`doi.get_doi_ref`
   - :func:`datatracker.internet_drafts.get_internet_draft`
