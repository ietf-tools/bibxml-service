"""
This module registers :func:`~.to_xml_string`
in this project’s serializer registry (:mod:`bib_models.serializers`).
"""
from typing import List

from lxml.etree import _Element
from lxml import objectify, etree
from relaton.models import Relation
from relaton.serializers.bibxml.anchor import get_suitable_anchor
from relaton.serializers.bibxml.reference import create_referencegroup, create_reference
from relaton.serializers.bibxml.target import get_suitable_target
from relaton.util import as_list

from bib_models import serializers, BibliographicItem


__all__ = (
    'to_xml_string',
)


def serialize(item: BibliographicItem, anchor: str = None) -> _Element:
    """Converts a BibliographicItem to XML,
    trying to follow RFC 7991.

    Returned root element is either a ``<reference>``
    or a ``<referencegroup>``.

    :param str anchor: resulting root element ``anchor`` property.

    :raises ValueError: if there are different issues
                        with given item’s structure
                        that make it unrenderable per RFC 7991.
    """

    relations: List[Relation] = as_list(item.relation or [])

    constituents = [rel for rel in relations if rel.type == 'includes']

    is_referencegroup = len(constituents) > 0

    if is_referencegroup:
        root = create_referencegroup([
            ref.bibitem
            for ref in constituents
        ])
    else:
        root = create_reference(item)

    # Fill in default root element anchor, unless specified
    if anchor is None:
        try:
            anchor = get_suitable_anchor(item)
        except ValueError:
            pass
    if anchor:
        root.set('anchor', anchor)

    # Fill in appropriate target
    try:
        target = get_suitable_target(as_list(item.link or []))
    except ValueError:
        pass
    else:
        root.set('target', target)

    objectify.deannotate(root)
    etree.cleanup_namespaces(root)

    return root


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
