===========================================
How to add new output format support to API
===========================================

Default serialization method is Relaton JSON.

There is support for pluggable additional serialization methods.

1. Define a serializer function. It must accept
   a :class:`relaton.models.bibdata.BibliographicItem` instance
   as a positional argument, arbitrary keyword arguments
   (which it may use or not), and return an utf8-encoded string.

2. Register your serializer like this::

       from typing import Tuple
       from bib_models import serializers
       from relaton.models import BibliographicItem

       @serializers.register('foobar', 'application/x-foobar')
       def to_foobar(item: BibliographicItem, **kwargs) -> str:
           serialized: str = some_magic(item)
           return serialized

   .. note:: Make sure the module that does the registration is imported at startup
             (use ``app.py`` if it’s a Django app, or project-wide ``bibxml.__init__``).
 
   In the above example, we associate serializer with ID “foobar”,
   meaning API callers will be able to specify ``format=foobar`` in GET parameters,
   and content type ``application/json``, meaning that will be the MIME type of response they receive.

.. seealso:: :rfp:req:`16`
