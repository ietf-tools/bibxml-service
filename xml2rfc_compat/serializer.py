"""
This module registers :func:`~.to_xml_string`
in this project’s serializer registry (:mod:`bib_models.serializers`).
"""
from lxml import etree

from bib_models import serializers, BibliographicItem


__all__ = (
    'to_xml_string',
)

from xml2rfc_compat.serializers import serialize


@serializers.register('bibxml', 'application/xml')
def to_xml_string(item: BibliographicItem, **kwargs) -> bytes:
    """
    A wrapper around :func:`xml2rfc_compat.serializer.serialize`.
    """
    # get a tree
    canonicalized_tree = etree.fromstring(
        # obtained from a canonicalized string representation
        etree.tostring(
            # of the original bibxml tree
            serialize(item, **kwargs),
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
