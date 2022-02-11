========================================
How to adjust xml2rfc-style path parsing
========================================

Do you have xml2rfc-style paths which result in fallback behavior?

You may need to make it resolve to a Relaton bibliographic item obtained
from up-to-date sources.

- If it’s a general case
  and the :term:`xml2rfc anchor`
  is enough to deduce Relaton bibliographic item lookup,
  edit the fetcher function:
  adjust the query e.g. by adding an OR condition.

  Use root URL config to locate which fetcher function is responsible
  for the subdirectory in question.

- Otherwise, you can create a manual mapping
  using the xml2rfc path resolution management GUI.

  Locate an item using service’s general-purpose search functionality,
  and copy the first citeable identifier
  from bibliographic item details page.

  Use that identifier when creating a mapping.

.. seealso::

   - :doc:`/topics/xml2rfc-compat`
   - :mod:`xml2rfc_compat`
