"""
Registers :func:`relaton.serializers.bibxml_string.serialize`
in this project’s serializer registry.
"""

from relaton.serializers.bibxml_string import serialize
from bib_models import serializers, BibliographicItem


__all__ = (
    'to_xml_string',
)


@serializers.register('bibxml', 'application/xml')
def to_xml_string(item: BibliographicItem, **kwargs) -> bytes:
    """
    Delegates to ``relaton-py`` implementation
    of :mod:`relaton.serializers.bibxml_string` serializer.
    """
    return serialize(item, **kwargs)
