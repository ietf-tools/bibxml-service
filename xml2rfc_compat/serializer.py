"""
Registers to_xml_string in this project’s serializer registry.
"""
from lxml import etree
from relaton.serializers.bibxml import serialize as _original_serialize
from bib_models import serializers, BibliographicItem


__all__ = (
    'to_xml_string',
)


@serializers.register('bibxml', 'application/xml')
def to_xml_string(item: BibliographicItem, **kwargs) -> bytes:
    # get a tree
    canonicalized_tree = etree.fromstring(
        # obtained from a canonicalized string representation
        etree.tostring(
            # of the original bibxml tree
            _original_serialize(item, **kwargs),
            method='c14n2',
        )
        # ^ this returns a unicode string
    )

    # pretty-print that tree in utf-8 without declaration and doctype
    return etree.tostring(
        canonicalized_tree,
        encoding='utf-8',
        xml_declaration=False,
        doctype=None,
        pretty_print=True,
    )
