import re
from typing import List, Tuple, Callable, Optional


__all__ = (
    'get_suitable_anchor',
    'to_valid_xsid',
    'XSID_REGEX',
    'XSID_ILLEGAL',
    'ANCHOR_FORMATTERS',
)

from relaton.models import BibliographicItem, DocID

from common.util import as_list


def get_suitable_anchor(item: BibliographicItem) -> str:
    """From a :class:`~relaton.models.bibdata.BibliographicItem` instance
    get best anchor value and return it as a string.

    Tries :data:`~.ANCHOR_FORMATTERS`, and if none return a string
    then takes the first primary ``docid``,
    (or the first ``docid`` with ``scope`` equal to “anchor”,
    or just the first docid).

    Ensures the value matches XSID schema.

    :param item: a :class:`bib_models.bibdata.BibliographicItem` instance
    :returns str: a string to be used as anchor
    :rtype: str
    :raises ValueError: unable to obtain an anchor, e.g. item has no docids
    """

    docids: List[DocID] = as_list(item.docid or [])

    try:
        anchor_docid: str = (
            # Prefer bespoke
            [custom_anchor
                for d in docids
                for formatter in ANCHOR_FORMATTERS
                if (custom_anchor := formatter(d))]
            # Otherwise, prefer primary
            or [d.id for d in docids
                if d.primary
                and XSID_REGEX.match(d.id) is not None]
            # Fallback case (docid.scope may be going away)
            or [d.id for d in docids
                if getattr(d, 'scope', '') == 'anchor'
                and XSID_REGEX.match(d.id) is not None]
            # Otherwise, take any docid
            or [d.id for d in docids])[0]
    except IndexError:
        raise ValueError("No suitable anchor could be determined")
    else:
        if XSID_REGEX.match(anchor_docid) is not None:
            return anchor_docid
        else:
            return to_valid_xsid(anchor_docid)


def to_valid_xsid(val: str) -> str:
    """
    Transforms a string into a valid xs:id value.
    Transformation is lossy and irreversible.
    """
    return XSID_ILLEGAL.sub('', re.sub(
        r'^\d',
        r'_\g<0>',
        re.sub(
            r'[-\s]+',
            '_',
            val
            .replace('/', '-')
            .replace(':', '.')
            .strip('-_')
        )
    ))


XSID_REGEX = re.compile(r'^[a-zA-Z_][-.\w]*$')
"""A regular expression matching a full valid xs:id value."""

XSID_ILLEGAL = re.compile(r'[^-.\w]')
"""A regular expression matching xs:id characters that are invalid
anywhere within an xs:id string."""

ANCHOR_FORMATTERS: Tuple[Callable[[DocID], Optional[str]]] = (
    (lambda docid:
        f"RFC{docid.id.split(' ')[1].zfill(4)}"
        if all([
            docid.primary,
            docid.type == 'IETF',
            docid.id.startswith('RFC '),
        ])
        else None),
)
"""Custom anchor formatters.
Each function must take a :class:`relaton.models.bibdata.DocID`
instance and produce either an anchor string or ``None``.
"""
