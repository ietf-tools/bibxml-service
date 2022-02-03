=======================
How to add a new source
=======================

New Relaton source
==================

For a Relaton source that conforms to the same layout
as existing ``ietf-ribose/relaton-data-*``/``ietf-ribose/bibxml-data-*``
repositories on GitHub, it should be sufficient to add
new source ID under :data:`bibxml.settings.RELATON_DATASETS`.

New source ID must not clash with any of the other IDs
of an internal or external source,
and requires that both repositories
``ietf-ribose/relaton-data-<your source ID>``
and ``ietf-ribose/bibxml-data-<your source ID>``
exist and use the exact same layout as the preexisting data repositories.

Other sources
=============

Currently, only sources backed by Git are supported.

If your source uses a Git repository (or multiple),
define your custom indexing and cleanup functions
and register them using :func:`sources.indexable.register_git_source`.

Registered source will be possible to reindex from management GUI and API.

If your source provides bibliographic data in Relaton format,
your source should create a :class:`main.models.RefData` instance for each
indexed item (make sure to use your source ID as ``dataset`` value).
This will make indexed bibliographic data available via service
retrieval API and GUI.

.. note:: If your source does **not** provide bibliographic data in Relaton format,
          you should make conversion to Relaton part of your indexing logic.

          Not doing so is recommended only in data migration fallback scenarios:
          for an example of that, see :mod:`xml2rfc_compat`,
          which registers its own Git-based source
          and uses it for xml2rfc-style path fallback.
