=============
Data sourcing
=============

The sources that power service’s API and GUI
can be divided into three categories:

- Indexable source of bibliographic data in Relaton format
- Indexable source of non-Relaton data
- External source of bibliographic data

.. contents::
   :local:

Indexable sources
=================

BibXML service’s own PostgreSQL database serves as more of a cache,
with data periodically indexed into it from indexable sources.

An indexable source must be registered and associated with
the function that handles the indexing via
:func:`sources.indexable.register_git_source()`.
After that, it appears in management GUI and API,
and its indexing can be queued.

When BibXML service is instructed to reindex any indexable source,
it queues an asynchronous task
that pulls or clones the relevant repositories and runs specified indexer function
that reads the data and populates the database.

Currently, any indexable source must be a Git repository.

.. seealso:: :mod:`sources.indexable` for indexable source registry implementation

.. seealso:: :doc:`/howto/auto-reindex-sources`

There are two types of indexable sources:

Bibliographic data sources
--------------------------

These are Relaton sources registered in :mod:`main.sources`.

These sources provide bibliographic data exposed in service’s GUI.
Each underlying repository contains bibliographic data in :term:`Relaton format`,
serialized as YAML, under ``data/`` directory in repository root.
They are periodically updated by external tools outside of BibXML service
from authoritative bibliographic data sources.

The full list of Relaton sources is provided in :data:`bibxml.settings.RELATON_DATASETS`.
For every item in that list, a repository URL can be obtained
using the approach in :func:`main.sources.locate_relaton_source_repo()`: the common case
is ``https://github.com/ietf-tools/relaton-data-{dataset ID}`` with branch name ``main``
(where “dataset ID” is the string from ``RELATON_DATASETS``),
unless an override is specified in :data:`bibxml.settings.DATASET_SOURCE_OVERRIDES`
for that dataset ID (in which case that setting will have ``relaton_data.repo_url``
specifying URL and/or branch name explicitly).

.. seealso:: :mod:`main.sources` for Relaton source registration & indexing logic

.. _sourcing-xml2rfc-archive:

xml2rfc archive source
----------------------

Also called “:term:`xml2rfc mirror source`”,
this source provides xml2rfc compatibility related data—preexisting xml2rfc paths
with original XML contents and how they map to Relaton document identifiers.

It’s not categorized as a bibliographic data source:
unlike with Relaton sources, this service deosn’t parse the original XML files
to extract bibliographic data for search.

The only way those XML files are used
is to return valid data for a preexisting xml2rfc path
that failed to resolve to an authoritative source.
In that scenario, XML string is returned verbatim
(except the anchor attribute may be substituted, if overridden via GET query).

Additionally, :term:`sidecar YAML <xml2rfc sidecar metadata file>` files
can be used to map some xml2rfc paths to Relaton document identifiers
for faster and more reliable path resolution.

See :ref:`xml2rfc-path-resolution-algorithm` for more on xml2rfc path resolution.

.. seealso:: :mod:`xml2rfc_compat.source` for this source’s registration & indexing logic

.. _sourcing-external-sources:

External sources
================

External sources don’t make bibliographic data available
in bulk in Relaton format, but they still make bibliographic data available for querying
via API.

Examples of such sources are Datatracker (providing Internet Draft data)
and Crossref (providing DOI data).
IANA’s assignments API is also a candidate for implementation as an external source.

An external source is registered in external source registry
using :func:`main.external_sources.register_for_types()`.
Registration of an external source associates it with:

- a unique source ID,
- a particular :term:`document identifier type`, and
- a function that, given a :term:`docid.id` and a ``strict`` parameter, makes the necessary requests
to external services and returns an :class:`main.types.ExternalBibliographicItem` instance
constructed from response data.

Subsequently, registered external sources can be queried
by calling :func:`main.external_sources.ExternalSource.get_item()` with a :term:`docid.id` string.
For example, :func:`main.views.browse_external_reference` does that, allowing users
to request a DOI.

(In future external sources can be used in other ways, such as
to augment the native bibliographic item discovery interface
that currently only uses indexable sources.)

.. seealso::

   - :func:`doi.get_doi_ref`
   - :func:`datatracker.internet_drafts.get_internet_draft`
   - :mod:`main.external_sources`
