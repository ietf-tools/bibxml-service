"""
Some of Relaton’s bibliographic item specifications implemented
as typed dictionaries, dataclasses and Pydantic models.

They are mixed for a few reasons:

- Since we don’t want to always validate every item we instantiate,
  we can’t use Pydantic’s models for simpler types,
  so we use plain dataclasses.
- Where we encounter reserved words, we use ``TypedDict()``
  instantiations. They have a big drawback (no defaults on optionals),
  so their use is as limited as possible.
- Dataclass instantiation causes ugly ``TypeError``s when given
  unexpected data, which is especially bad at root model level.
  That, and generally Pydantic’s support for dataclasses
  is poor—so we use regular Pydantic models at higher levels.

.. note::

   Docstrings for dataclasses and models within this module
   may be used when rendering OpenAPI schemas,
   where ReSTructuredText syntax is not
   supported. Stick to plain text.

.. important:: Dumping a model as a dictionary using Pydantic
               does not dump any members that are dataclass instances.
               To obtain a full dictionary,
               use :func:`common.pydantic.unpack_dataclasses` utility.
"""
