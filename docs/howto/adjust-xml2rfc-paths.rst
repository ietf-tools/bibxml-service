========================================
How to adjust xml2rfc-style path parsing
========================================

Do you have xml2rfc-style paths which result in fallback behavior?

You may need to make it resolve to a Relaton bibliographic item obtained
from up-to-date sources.

1. Use root URL config to locate which fetcher function is responsible
   for the subdirectory in question.

2. Edit fetcher function. If general case
   and anchor is enough to deduce Relaton bibliographic item lookup,
   adjust the query e.g. by adding an OR condition.
   Otherwise you can add a special case
   and retrieve an exact bibliographic item by document ID
   from given anchor.

.. seealso::

   - :doc:`/topics/xml2rfc-compat`
   - :mod:`xml2rfc_compat`
