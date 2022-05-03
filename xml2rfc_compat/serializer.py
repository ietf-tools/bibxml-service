"""
Registers :func:`relaton.serializers.bibxml_string.serialize`
in this project’s serializer registry.
"""

import datetime
from relaton.serializers.bibxml_string import serialize
from bib_models import serializers, BibliographicItem


__all__ = (
    'to_xml_string',
)


@serializers.register('bibxml', 'application/xml')
def to_xml_string(item: BibliographicItem, **kwargs) -> bytes:
    """
    Passes given item and any kwargs through to :func:`.to_xml()`,
    and renders the obtained XML element as a string with pretty print.
    """
    return serialize(item, **kwargs)
