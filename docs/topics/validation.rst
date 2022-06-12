=============================
Bibliographic data validation
=============================

This service deals with bibliographic data obtained
from different sources compiled by external tools.

The data models defined (see :mod:`bib_models`)
handle data validation automatically, meaning constructed
bibliographic items can be assumed to have the expected properties
of correct types.

In some scenarios, source data may not validate.
This could be due to an error in the code (external or internal)
that constructs source data, or due to backwards-incompatible changes
in Relaton model (in case an external source conforms to a newer version of the spec,
while this service expects a previous version).

.. _strict-validation:

Strict validation with the “``strict``” parameter
=================================================

To make such situations less problematic,
some functions responsible for constructing bibliographic item instances
support a ``strict`` boolean keyword argument.

By default it is ``True``, and any item that fails validation
will make the function raise a :class:`pydantic.ValidationError`.
The caller should never receive a malformed item.

If explicitly set to ``False``, the item will be constructed anyway,
but it may contain unexpected data types. For example, it may
have dictionaries instead of objects, or timestamps as strings
instead of appropriate datetime objects.

.. note::

   Setting ``strict=False`` is intended for cases like forgiving template rendering,
   and is not recommended if returned item is to be used programmatically.

.. seealso::

   Some functions that use ``strict``:

   - :func:`main.query.build_citation_for_docid`
   - :func:`main.query.get_indexed_item`
   - :func:`main.query_utils.merge_refs`
   - :func:`datatracker.internet_drafts.get_internet_draft`
   - :func:`doi.get_doi_ref`
