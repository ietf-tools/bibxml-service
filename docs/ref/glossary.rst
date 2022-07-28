========
Glossary
========

.. seealso:: :doc:`relaton:glossary` in ``relaton-py`` library documentation

.. glossary::

   bibliographic data source
   dataset
       Where BibXML service obtains bibliographic items to show the user
       as a result of a query.

       - More than one source can provide data for the bibliographic items
         with the same :term:`document identifier`.
       - One source can provide bibliographic items of more than one document type.

       Can either be an :term:`indexable source` or an :term:`external source`.

   Relaton format
       The normalized format used to store bibliographic data internally.
       See :doc:`/topics/relaton-format`.

   BibXML format
       XML using schema defined
       by `RFC 7991 <https://datatracker.ietf.org/doc/html/rfc7991>`_
       or newer `Xml2rfc vocabulary <https://xml2rfc.tools.ietf.org/xml2rfc-doc.html>`_.

   indexable source
       See :doc:`/topics/sourcing` for details.

   indexed source
       An :term:`indexable source` that has been indexed.

   reference
   ref
       Name of an entry in an :term:`indexed source`
       (e.g., a filename in a Git repository).
       Unique per source.

       In case of Relaton sources, reference data
       is indexed as :class:`main.models.RefData` instances.

       .. note:: Being a dataset-specific reference (such as a filename),
                 it is not expected to be known by the user. Hence, user searches
                 should not use :term:`ref`, but instead use
                 a :term:`document identifier`.

       .. seealso::

          :func:`main.query.get_indexed_item` retrieves a bibliographic item
          matching given source and source-specific reference, if it is indexed.

   external source
   external dataset
       See :ref:`sourcing-external-sources` for details.

   xml2rfc-style path
   legacy path
       A path that used to be handled by xml2rfc tools web server.
       (Normally points to an XML file.)

       Usually means the part of the URL *excluding*
       domain name and leading :data:`bibxml.settings.XML2RFC_PATH_PREFIX`.

       .. seealso::

          - :rfp:req:`5` for background
          - :doc:`/topics/xml2rfc-compat` for overview
          - :data:`xml2rfc_compat.models.dir_subpath_regex` for the regular expression

   xml2rfc archive source
   xml2rfc mirror source
      An :term:`indexable source` (living in a Git repository)
      that contains two kinds of data:

      (Not really a mirror, since its contents are not supposed
      to receive any updates.)

      - Original XML files as served by xml2rfc tools web server.

        These files are supposed to be periodically overwritten using rsync
        from rsync mirror.

      - :term:`Optional “sidecar” YAML files <xml2rfc sidecar metadata file>`.

      Read more in :ref:`sourcing-xml2rfc-archive`.

      .. seealso:: :mod:`xml2rfc_compat.source`

   xml2rfc sidecar metadata file
      A YAML file named after an XML file existing in :term:`xml2rfc archive source`,
      describing e.g. which bibliographic item it maps to.

      Among other things, it can describe which :term:`document identifier`
      the relevant XML file maps to, in order for the service to prefer an up-to-date
      document if it exists
      among available indexed :term:`bibliographic data sources <bibliographic data source>`.

      These YAML files can be edited using external tooling or by hand,
      and are not overwritten when xml2rfc archive source is automatically updated.

      .. seealso::

         - :attr:`xml2rfc_compat.models.Xml2rfcItem.sidecar_meta`
         - :class:`xml2rfc_compat.types.Xml2rfcPathMetadata`


   xml2rfc dirname
      For an :term:`xml2rfc-style path` like ``/public/rfc/bibxml3/reference.foo.bar.xml``,
      this is the “bibxml3” part.

      Some dirnames have aliases: e.g., ``bibxml4`` is equivalent to ``bibxml-w3c``.

      .. seealso:: :mod:`xml2rfc_compat.aliases`, :data:`bibxml.settings.XML2RFC_COMPAT_DIR_ALIASES`

   anchor
   xml2rfc anchor
      Used to mean two different strings, which may be the same
      but are conceptually different:

      - Part of the filename in an :term:`xml2rfc-style path`,
        without “reference” or “_reference” prefix and file extension.
      - The value of the “anchor” attribute on the ``<reference>``
        element in BibXML.

   xml2rfc adapter
      A set of functions registered and associated with :term:`xml2rfc dirname`
      via :func:`xml2rfc_compat.adapters.register_adapter`.

      Generally should be a :class:`xml2rfc_compat.adapters.Xml2rfcAdapter` subclass.

      Consists of resolve and reverse functions.

      Resolve function is invoked when handling a request to an xml2rfc path.
      It’s passed the ``anchor`` argument as a string,
      for which it must return a representation of the corresponding
      bibliographic item in :term:`BibXML format`.

      Reverse function is invoked when displaying a bibliographic item to the user,
      to obtain an xml2rfc path through which the same item can be obtained.
      It’s passed a :class:`relaton.models.bibdata.BibliographicItem` instance,
      and should return the :term:`anchor` part of xml2rfc-style path filename,
      or ``None`` if it’s not applicable to given item.

      .. seealso:: :ref:`xml2rfc-path-resolution-algorithm`
