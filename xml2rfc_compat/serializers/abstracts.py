from typing import List, cast

from lxml import etree, objectify
from lxml.etree import _Element
from relaton.models import GenericStringValue

__all__ = (
    'create_abstract',
)

E = objectify.E


JATS_XMLNS = "http://www.ncbi.nlm.nih.gov/JATS1"


def create_abstract(abstracts: List[GenericStringValue]) -> _Element:
    """
    Formats an ``<abstract>`` element.
    """
    if len(abstracts) < 1:
        raise ValueError("No abstracts are available")

    # Try to pick an English abstract, or the first one available
    abstract = (
        [a for a in abstracts if a.language in ('en', 'eng')] or
        abstracts
    )[0]

    return E.abstract(*(
        E.t(p)
        for p in get_paragraphs(abstract)
    ))


def get_paragraphs(val: GenericStringValue) -> List[str]:
    """Converts HTML or JATS to a list of strings representing
    paragraphs.
    """
    try:
        match val.format:
            case 'text/html':
                return get_paragraphs_html(val.content)
            case 'application/x-jats+xml':
                return get_paragraphs_jats(val.content)
            case _:
                raise ValueError("Unknown format for paragraph extraction")

    except (etree.XMLSyntaxError, ValueError):
        return get_paragraphs_plain(val.content)


def get_paragraphs_html(val: str) -> List[str]:
    tree = etree.fromstring(f'<main>{val}</main>')
    ps = cast(List[str], [
        p.text for p in tree.findall('p')
        if (getattr(p, 'text', '') or '').strip() != ''
    ])
    if len(ps) > 0:
        return ps
    else:
        raise ValueError("No HTML paragraphs detected")


def get_paragraphs_jats(val: str) -> List[str]:
    tree = etree.fromstring(f'<main xmlns:jats="{JATS_XMLNS}">{val}</main>')
    ps = cast(List[str], [
        p.text for p in tree.findall('jats:p', {'jats': JATS_XMLNS})
        if (getattr(p, 'text', '') or '').strip() != ''
    ])
    if len(ps) > 0:
        return ps
    else:
        raise ValueError("No JATS paragraphs detected")


def get_paragraphs_plain(val: str) -> List[str]:
    return [
        p.strip()
        for p in val.split('\n\n')
        if p.strip() != ''
    ]
