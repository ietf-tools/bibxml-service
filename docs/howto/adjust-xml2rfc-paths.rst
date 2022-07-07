========================================
How to adjust xml2rfc-style path parsing
========================================

Do you have xml2rfc-style paths which result in fallback behavior?

You may need to make it resolve to a Relaton bibliographic item obtained
from up-to-date sources.

- If it’s a general case
  and the :term:`xml2rfc anchor`
  is enough to deduce Relaton bibliographic item lookup,
  edit the adapter subclass (in particular, the ``resolve()`` method):
  adjust the query e.g. by adding an OR condition.

  .. seealso:: :mod:`bibxml.xml2rfc_adapters`

- Otherwise, you can create a manual mapping
  by updating sidecar metadata YAML file within :term:`xml2rfc mirror source`
  repository (and reindexing the source in BibXML service).

  1. Locate an item using service’s general-purpose search functionality,
     and copy the first citeable identifier
     from bibliographic item details page.

  2. Use that identifier when creating a YAML file with contents like this::

         primary_docid: "<copied string>"

.. seealso::

   - :doc:`/topics/xml2rfc-compat`
   - :mod:`xml2rfc_compat`
