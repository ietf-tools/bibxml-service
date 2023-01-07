"""Serialization of :class:`relaton.models.bibdata.BibliographicItem`
into BibXML (xml2rfc) format roughly per RFC 7991,
with bias towards existing xml2rfc documents where differs.

Primary API is :func:`.serialize()`.

.. seealso:: :mod:`~relaton.serializers.bibxml_string`
"""

from typing import List, Optional

from lxml import objectify, etree
from lxml.etree import _Element
from relaton.models import Relation

from common.util import as_list
from .anchor import get_suitable_anchor
from .reference import create_reference, create_referencegroup
from .target import get_suitable_target
from bib_models import BibliographicItem

__all__ = (
    'serialize',
)


def serialize(item: BibliographicItem, anchor: Optional[str]) -> _Element:
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
