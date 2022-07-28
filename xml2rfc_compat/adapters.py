"""Implements a registry of xml2rfc-style path adapters.

Plug registered adapters into root URL configuration
via :func:`xml2rfc_compat.urls.get_urls()`.
"""

from typing import Dict, List, Tuple, Optional, TypeAlias, Type, Sequence
import logging
import re

from django.urls import reverse, NoReverseMatch

from relaton.models.bibdata import BibliographicItem, DocID

from bib_models.util import get_primary_docid
from common.util import get_fuzzy_match_regex

from main.models import RefData
from main.query_utils import compose_bibitem
from main.query import hydrate_relations, search_refs_relaton_field
from main.exceptions import RefNotFoundError

from .models import Xml2rfcItem, construct_normalized_xml2rfc_subpath


log = logging.getLogger(__name__)


ReversedRef: TypeAlias = Tuple[str, Optional[str]]
"""Describes a reversed xml2rfc path, possibly with a description."""


class Xml2rfcAdapter:
    """
    Base adapter class. Intended to be subclassed,
    as default logic is insufficient.

    An adapter is instantiating during each xml2rfc path request
    (see :func:`xml2rfc_compat.views.handle_xml2rfc_path`).
    """

    dirname: str
    """Directory name :data:`xml2rfc_compat.models.dir_subpath_regex`."""

    subpath: str
    """The entire subpath in :data:`xml2rfc_compat.models.dir_subpath_regex`,
    with possible underscore in ``_reference`` stripped."""

    anchor: str
    """The anchor part of :data:`xml2rfc_compat.models.dir_subpath_regex`."""

    resolved_item: Optional[BibliographicItem] = None
    """
    After calling :meth:`.resolve()`, this attribute
    may be populated with resolved item, if any.
    """

    exact_docid_match: bool = False
    """
    If True, then default behavior is to match
    the docid.id obtained from ``resolve_docid()`` exactly
    (unless you override ``get_docid_query()`` or others).

    If False, a case-insensitive regex query is used
    to match ID parts split by punctuation/special characters.
    This is fuzzier and can lead to false positives.
    """

    _log: List[str]

    def __init__(self, subpath: str, dirname: str, anchor: str):
        self.dirname = dirname
        self.subpath = subpath
        self.anchor = anchor
        self._log = []

    # Public

    def resolve(self) -> BibliographicItem:
        """
        Resolves to bibliographic item.
        """
        refs = self.fetch_refs()
        if (num_refs := len(refs)):
            self.log(f"{num_refs} found")
            return self.build_bibitem(refs)
        else:
            self.log("no refs found")
            raise RefNotFoundError()

    def format_anchor(self) -> Optional[str]:
        """
        If service requires a different anchor attribute value
        than default Relaton’s serializer returns,
        this method can provide it.

        ``self.resolved_item`` may be available when this method is called.
        """
        return None

    def mangle_anchor(self, anchor: str) -> str:
        """
        Performs final anchor mangling,
        regardless of how the anchor was obtained.

        By default, does minimal substitutions to attempt to comply
        with ``xs:ID`` schema.
        """
        return re.sub(
            r'^\d',
            r'_\g<0>',
            anchor.
            replace(' ', '.').
            replace(':', '.')
        )

    @classmethod
    def reverse(
        cls,
        item: BibliographicItem,
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Returns a list of xml2rfc path filename anchors
        that would resolve to given item.

        (Paths contain no /public/rfc/ or dirname prefix,
        nor xml extension.)

        :returns:
            List of :data:`.ReversedRef` tuples,
            empty if adapter doesn’t account for given item.

        :rtype: List[ReversedRef]
        """
        if (docid := get_primary_docid(item.docid)):
            return [(f'{docid.type}.{docid.id}', None)]
        return []

    # Somewhat private/subclass-only

    def log(self, msg: str):
        self._log.append(msg)

    def fetch_refs(self) -> Sequence[RefData]:
        if (query := self.get_docid_query()):
            self.log(f"using query {query}")
            return search_refs_relaton_field({
                'docid[*]': query,
            }, limit=10, exact=True)
        return []

    def get_docid_query(self) -> Optional[str]:
        if (docid := self.resolve_docid()):
            if isinstance(docid, list):
                queries: List[str] = []
                for d in docid:
                    self.log(f"using docid {d.type} {d.id}")
                    queries.append(get_docid_query(
                        d,
                        exact=self.exact_docid_match))
                query = ' || '.join([f'({q})' for q in queries])
            else:
                self.log(f"using docid {docid.type} {docid.id}")
                query = get_docid_query(
                    docid,
                    exact=self.exact_docid_match)

            return query
        else:
            return None

    def resolve_docid(self) -> List[DocID] | Optional[DocID]:
        doctype, docid = self.anchor.split('.', 1)
        return DocID(type=doctype, id=f'{doctype} {docid}')

    def build_bibitem(self, refs: Sequence[RefData]) -> BibliographicItem:
        if len(refs) > 0:
            composite_item, valid = compose_bibitem(refs, strict=True)
            self.resolved_item = composite_item
            # Ensure relations are full
            if valid and composite_item.relation:
                hydrate_relations(
                    composite_item.relation,
                    strict=True,
                    depth=1,
                    resolved_item_cache={},
                )
            return composite_item
        else:
            raise ValueError("No refs given")


adapters: Dict[str, Type[Xml2rfcAdapter]] = {}
"""Registered adapter classes."""


def register_adapter(dirname: str):
    """Parametrized decorator that registers an adapter class."""
    def _register_xml2rfc_adapter(cls):
        adapters[dirname] = cls
        return cls
    return _register_xml2rfc_adapter


def get_docid_query(docid: DocID, exact=False) -> str:
    q = '@.type == "%s" && @.primary == true' % docid.type
    if exact:
        return '%s && @.id == "%s"' % (q, docid.id)
    else:
        return '%s && @.id like_regex "(?i)^%s$"' % (
            q,
            get_fuzzy_match_regex(docid.id),
        )


def make_xml2rfc_url(
    dirname: str,
    subpath: str,
    desc: Optional[str] = None,
    request=None,
) -> Optional[Tuple[str, str, Optional[str]]]:
    try:
        # Use Django’s ``reverse()`` to ensure all
        # returned xml2rfc paths actually resolve
        url = reverse(
            f'xml2rfc_{dirname}',
            args=[subpath],
        )
        return (
            subpath,
            request.build_absolute_uri(url)
            if request else url,
            desc,
        )
    except NoReverseMatch:
        # XXX: Log reversion failure
        log.exception("Failed to reverse xml2rfc path")
        return None


def list_xml2rfc_urls(
    item: BibliographicItem,
    request=None,
) -> List[Tuple[str, str, Optional[str]]]:
    """
    For given :class:`relaton.models.bibdata.BibliographicItem`,
    returns a list of 3-tuples of strings (URL subpath, URL, notes).

    Uses registered adapters’ :meth:`Xml2rfcAdapter.reverse()` methods,
    omitting any returned paths that fail to ``django.urls.reverse()``.

    If ``request`` is given, the second string is a full URL
    with domain (otherwise, it’s a relative path).
    """
    urls: List[Tuple[str, str, Optional[str]]] = []

    # Use reverse mapping, if any
    if ((
        docid := get_primary_docid(item.docid)
    ) and (
        xml2rfc_item := Xml2rfcItem.objects.
        filter(sidecar_meta__primary_docid=docid.id).
        first()
    ) and (
        url := make_xml2rfc_url(
            xml2rfc_item.format_dirname(),
            xml2rfc_item.subpath,
            None,
            request)
    )):
        urls.append(url)

    # Try adapters’ automatic reversion
    if not urls:
        for dirname, adapter_cls in adapters.items():
            if reversed_anchors := adapter_cls.reverse(item):
                urls.extend([
                    url
                    for anchor, desc in reversed_anchors
                    if (url := make_xml2rfc_url(
                        dirname,
                        construct_normalized_xml2rfc_subpath(dirname, anchor),
                        desc,
                        request,
                    ))
                ])

    return urls
