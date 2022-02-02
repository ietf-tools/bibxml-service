========================
Citation metadata format
========================

The canonical citation representation is considered to be Relaton format.
The exact specification is in flux, but a rough outline is available
as a `RelaxNG grammar <https://github.com/relaton/relaton-models/blob/main/grammars/biblio.rnc>`_.

Among the key properties is ``docid``, which contains document identifier
in the shape of ``{ type: <document type>, id: <document ID> }``,
where type can be e.g. “IEEE”, and document ID is a freeform string
with shape depending on document type.

.. seealso:: :mod:`bib_models` for implementation of bibliographic item classes
             in Python with Pydantic validation.

.. note::

   Currently, Relaton specification for bibliographic item object
   does not specify a minimum required set of properties,
   treating all as optional.
