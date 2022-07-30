"""
Defines adapters for xml2rfc paths. See :term:`xml2rfc adapter`.
"""

from typing import Optional, List, cast, Sequence
import urllib
import logging
import re

from relaton.models.bibdata import BibliographicItem, DocID, VersionInfo

from bib_models.util import get_primary_docid
from doi.crossref import get_bibitem as get_doi_bibitem
from datatracker.internet_drafts import get_internet_draft
from datatracker.internet_drafts import remove_version
from main.models import RefData
from main.query import search_refs_relaton_field
from main.exceptions import RefNotFoundError

from xml2rfc_compat.adapters import register_adapter
from xml2rfc_compat.adapters import ReversedRef, Xml2rfcAdapter


log = logging.getLogger(__name__)


@register_adapter('bibxml')
class RfcAdapter(Xml2rfcAdapter):
    """
    Adapts RFC paths. Straightforward case of string replacement.
    """
    exact_docid_match = True

    def format_anchor(self):
        return self.anchor.replace('.', '')

    @classmethod
    def get_zero_filled_rfc_num(cls, item: BibliographicItem) -> Optional[str]:
        if ((docid := get_primary_docid(item.docid))
                and docid.type == 'IETF'
                and docid.id.startswith('RFC ')):
            return docid.id.split(' ')[1].zfill(4)
        return None

    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        return (
            [(f"RFC.{num}", None)]
            if (num := cls.get_zero_filled_rfc_num(item))
            else [])

    def resolve_docid(self) -> Optional[DocID]:
        parts = self.anchor.split('.')
        if parts[0] == 'RFC' and len(parts[1]) == 4:
            raw_num = parts[1]
            rfc_num = int(raw_num)
            return DocID(type="IETF", id=f"RFC {rfc_num}")
        else:
            return None


@register_adapter('bibxml2')
class MiscAdapter(Xml2rfcAdapter):
    """
    Resolves misc paths. ID is fuzzy matched.
    """

    IGNORE_DOCTYPES = set([
        'IANA',
        'W3C',
        'IETF',
        'Internet-Draft',
        '3GPP',
        'IEEE',
        'NIST',
    ])
    """These doctypes will not be reversed.
    It’s expected that they will be reversed by other, more specific adapters.

    (So that, e.g., for a W3C doc, user won’t see a bibxml-misc path
    in addition to bibxml4 path.)
    """

    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        if ((docid := get_primary_docid(item.docid))
                and docid.type not in cls.IGNORE_DOCTYPES):
            return [(f"{docid.id.replace(' ', '.')}", None)]
        return []


@register_adapter('bibxml3')
class InternetDraftsAdapter(Xml2rfcAdapter):
    """
    Paths should work as follows:

    - Unversioned I-D has path pattern: reference.I-D.xxx.xml
    - Versioned I-D has path pattern: reference.I-D.draft-xxx-nn.xml

    In the following cases, the path should return 404:

    - Unversioned I-D has path pattern: reference.I-D.draft-xxx.xml
    - Versioned I-D has path pattern: reference.I-D.xxx-nn.xml

    .. seealso:: :issue:`157`
    """

    anchor_is_valid: bool
    bare_anchor: str
    unversioned_anchor: str
    requested_version: Optional[str]

    def format_anchor(self):
        """
        Returns a string like ``I-D.foo-bar``,
        if full ID is e.g. ``draft-foo-bar-00``.
        This is in line with preexisting xml2rfc tools behavior.
        """
        return f"I-D.{self.unversioned_anchor}"

    @classmethod
    def get_bare_i_d_docid(self, item: BibliographicItem) -> Optional[str]:
        if ((primary_docid := get_primary_docid(item.docid))
                and primary_docid.type == 'Internet-Draft'):
            return remove_version(primary_docid.id.removeprefix("draft-"))[0]
        return None

    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        if (bare_id := cls.get_bare_i_d_docid(item)):
            if (version := item.version):
                # Return versioned path for I-D version
                return [(
                    f'I-D.draft-{bare_id}-{version[0].draft}',
                    None,
                )]
            else:
                # Return unversioned path for I-D umbrella item
                return [(
                    f"I-D.{bare_id}",
                    "Resolves to the latest available version "
                    "of this Internet Draft",
                )]
        return []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ref = self.anchor

        self.bare_anchor = ref.removeprefix('I-D.').removeprefix('draft-')
        unversioned, version = remove_version(self.bare_anchor)

        self.unversioned_anchor = unversioned
        self.requested_version = version

        self.anchor_is_valid = all([
            # all references must have the I-D. prefix:
            ref.startswith('I-D.'),
            any([
                # and must be either versioned
                # with the additional draft- prefix:
                ref.startswith('I-D.draft-') and version,
                # or unversioned without the additional draft- prefix:
                not ref.startswith('I-D.draft-') and not version,
            ]),
        ])

    def fetch_refs(self) -> Sequence[RefData]:
        unversioned = self.unversioned_anchor
        if version := self.requested_version:
            query = (
                '(@.type == "Internet-Draft") && '
                f'(@.id == "draft-{unversioned}-{version}")'
            )
            self.log(f"using query {query}")
            return list(search_refs_relaton_field({
                'docid[*]': query,
            }, limit=10, exact=True))
        else:
            query = (
                '(@.type == "Internet-Draft") && '
                r'(@.id like_regex "%s[[:digit:]]{2}")'
                % re.escape(f'draft-{unversioned}-')
            )
            self.log(f"using query {query}")
            return [sorted(
                search_refs_relaton_field({
                    'docid[*]': query,
                }, limit=50, exact=True),
                key=_sort_by_id_draft_number,
                reverse=True,
            )[0]]

    def resolve(self) -> BibliographicItem:
        """Returns either latest indexed version,
        or latest version at Datatracker if it’s newer.

        .. note:: Datatracker may provide less data than indexed sources.
        """
        if not self.anchor_is_valid:
            raise RefNotFoundError(
                "unsupported xml2rfc-style I-D reference: "
                "possibly missing I-D prefix "
                "or unexpected draft- prefix and trailing version combination")

        # Obtain the newest draft version available in indexed sources
        # (both bibitem data and version number)
        indexed_bibitem: Optional[BibliographicItem]
        indexed_version: Optional[str]

        # Look up by primary identifier
        try:
            indexed_bibitem = self.build_bibitem(self.fetch_refs())
        except Exception:
            log.exception(
                "Failed to obtain or validate indexed bibliographic item "
                "when resolving xml2rfc path for I-D %s", self.anchor)
            indexed_bibitem = None

        if indexed_bibitem and len(indexed_bibitem.version or []) > 0:
            indexed_version = cast(
                List[VersionInfo],
                indexed_bibitem.version)[0].draft
        else:
            log.error(
                "Indexed bibliographic item found "
                "when resolving xml2rfc path for I-D %s "
                "lacks I-D version", self.anchor)
            indexed_version = None

        # Check Datatracker’s latest version (slow)
        try:
            dt_bibitem = get_internet_draft(
                f'draft-{self.bare_anchor}',
                strict=indexed_bibitem is None,
            ).bibitem

            if len(dt_bibitem.version or []) > 0:
                dt_version = dt_bibitem.version[0].draft
                if not isinstance(dt_version, str):
                    raise ValueError(
                        "Malformed I-D version (not a string): "
                        f"{dt_version}")
                try:
                    parsed_version = int(dt_version)
                except (ValueError, TypeError):
                    raise ValueError(
                        "Malformed I-D version (doesn’t parse to an integer): "
                        f"{dt_version}")
                else:
                    if parsed_version < 0:
                        raise ValueError(
                            "Malformed I-D version (not a positive integer): "
                            f"{dt_version}")
            else:
                raise ValueError("Missing I-D version")

        except Exception:
            log.exception(
                "Failed to fetch or validate latest draft from Datatracker "
                "when resolving xml2rfc bibxml3 path")
        else:
            # Conditions for falling back to Datatracker’s response.
            # We want to prefer indexed items in general, because they tend to
            # provide more complete data, but in some cases we have no choice
            # but to fall back.
            if any([
                # We were not requested a version
                not self.requested_version,
                # We were requested a version and we got that version
                # from Datatracker
                self.requested_version == dt_version,
            ]) and any([
                # We did not find indexed item matching given ID
                # and maybe version:
                not indexed_bibitem,
                # We were not requested a version,
                # and latest version on Datatracker is different
                # (assuming newer):
                not self.requested_version
                and indexed_version != dt_version,
                # We were requested a version,
                # and somehow indexed version does not match requested version:
                self.requested_version
                and indexed_version != self.requested_version,
            ]):
                # Datatracker’s version is newer
                # or we don’t have this draft indexed.
                # Note this (should be transient until sources are reindexed,
                # if not then there’s a problem)
                # and return Datatracker’s version
                self.log(f"returning Datatracker version {dt_version}")
                log.warn(
                    "Returning Datatracker result for xml2rfc bibxml3 path. "
                    "If unversioned I-D was requested, "
                    "then Datatracker may have a newer I-D version "
                    "than indexed sources. "
                    "Alternatively, indexed version could not be used "
                    "for some reason. "
                    "Requested version %s, "
                    "indexed sources have version %s, "
                    "returning Datatracker’s version %s. ",
                    self.requested_version,
                    indexed_version,
                    dt_version)
                return dt_bibitem

        if indexed_bibitem and any([
            not self.requested_version,
            indexed_version == self.requested_version,
        ]):
            return indexed_bibitem
        else:
            raise RefNotFoundError()


@register_adapter('bibxml4')
class W3cAdapter(Xml2rfcAdapter):
    """
    Resolves W3C paths.
    """
    @classmethod
    def reverse(self, item: BibliographicItem) -> List[ReversedRef]:
        if ((docid := get_primary_docid(item.docid))
                and docid.type == 'W3C'):
            return [(f"W3C.{docid.id.removeprefix('W3C ')}", None)]
        return []

    # def get_docid_query(self) -> Optional[str]:

    def resolve_docid(self) -> DocID:
        unprefixed = self.anchor.removeprefix('W3C.')
        # We can try combinations w/o trailing date and/or leading doctype
        # for a fuzzy match:
        # untyped = (
        #     unprefixed.
        #     removeprefix('NOTE-').
        #     removeprefix('SPSR-').
        #     removeprefix('REC-').
        #     removeprefix('CR-').
        #     removeprefix('PR-').
        #     removeprefix('WD-'))
        # appear to not have the old versions in bibxml-w3c.
        # undated_untyped = re.sub(r'\-[\d]{8}$', '', untyped)
        # undated = re.sub(r'\-[\d]{8}$', '', unprefixed)
        return DocID(type="W3C", id=f'W3C {unprefixed}')


@register_adapter('bibxml5')
class ThreeGPPAdapter(Xml2rfcAdapter):
    """
    This scheme is very simple, and looks like ``[SDO-]3GPP.NN.MMM``.
    They in fact resolve to 3GPP TR or TS, followed by ``NN.MMM:Rel-...``,
    but apparently the NN.MMM parts don’t clash
    between TR and TS and the ``Rel-...`` part doesn’t matter.
    """

    @classmethod
    def resolve_num(cls, item: BibliographicItem) -> Optional[str]:
        if ((docid := get_primary_docid(item.docid))
                and docid.type == '3GPP'):
            return (
                docid.id.split(':')[0].
                removeprefix('3GPP ').
                removeprefix('TS ').
                removeprefix('TR ').
                replace(' ', '.'))
        return None

    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        if (num := cls.resolve_num(item)):
            return [
                (f"3GPP.{num}", None),
                (f"SDO-3GPP.{num}", None),
            ]
        return []

    def fetch_refs(self) -> Sequence[RefData]:
        docid = self.anchor.removeprefix('SDO-3GPP.').removeprefix('3GPP.')

        query = (
            '@.type == "3GPP" && ('
                '@.id like_regex "(?i)^3GPP (TR|TS) %s"'
            ')' % re.escape(docid)
        )
        self.log(f"using query {query}")
        return search_refs_relaton_field({
            'docid[*]': query,
            'date[*]': '@.type == "published"',
        }, limit=1, exact=True)

    def format_anchor(self) -> str:
        if self.resolved_item is not None:
            if num := self.resolve_num(self.resolved_item):
                return f'SDO-3GPP.{num}'
            else:
                raise RuntimeError("Cannot format anchor: failed to resolve num")
        else:
            raise RuntimeError("Cannot format anchor: item not resolved")


@register_adapter('bibxml6')
class IeeeAdapter(Xml2rfcAdapter):
    """
    Resolves IEEE documents via paths prefixed with ``R.``,
    which are considered reliably formatted but are not compatible
    with preexisting paths.

    - :term:`docid.id` -> :term:`xml2rfc anchor` conversion logic:

      1. Split the path into prefix and the rest of the anchor.

      2. In prefix, slashes are replaced with underscores, e.g.:

         - IEEE documents start with ``R.IEEE.``,
         - mixed-published documents start with e.g. ``R.ANSI_IEEE.``.

      3. The rest of the anchor is URL quoted
         (everything is percent-encoded except ASCII letters, numbers,
         basic punctuation like dash and forward slash).

      4. Prefix and rest are recombined, separated by period;
         and everything is prefixed with ``R.``.

    - xml2rfc anchor resolution logic:

      - For anchors that don’t start with ``R.``,
        adapter doesn’t resolve the xml2rfc path, letting the view fall back
        to archive XML data.

      - For anchors that start with ``R.``, as above in reverse.
    """

    exact_docid_match = True

    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        if ((docid := get_primary_docid(item.docid))
                and docid.type == 'IEEE'):
            prefix, rest = docid.id.split(' ', 1)
            anchor = f"R.{prefix.replace('/', '_')}.{urllib.parse.quote(rest)}"
            return [(
                anchor,
                "The R-prefixed xml2rfc path uses filenames "
                "derived from authoritative IEEE identifiers "
                "in a reversible manner.")]
        return []

    def resolve_docid(self) -> Optional[DocID]:
        is_legacy = not self.anchor.startswith('R.')
        if is_legacy:
            # We give up on automatically resolving legacy bibxml6/IEEE paths.
            # This is intended to trigger fallback behavior
            # for any path that is not manually mapped.
            return None
        else:
            # However, we support automatically generated IEEE paths
            # that we can be sure to resolve
            unprefixed = self.anchor.removeprefix('R.')
            id_prefix, rest = unprefixed.split('.', 1)
            return DocID(
                type="IEEE",
                id=f"{id_prefix.replace('_', '/')} {urllib.parse.unquote(rest)}",
            )


@register_adapter('bibxml8')
class IanaAdapter(Xml2rfcAdapter):
    """
    Resolves IANA paths.

    The forward slash that separates registry ID part from subregistry ID part
    in subregistry identifiers is replaced by underscore in xml2rfc paths.
    """
    exact_docid_match = True

    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        if ((docid := get_primary_docid(item.docid))
                and docid.type == 'IANA'):
            xml2rfc_anchor = 'IANA.' + (
                docid.id.
                removeprefix('IANA ').
                replace('/', '_')
            )
            return [(xml2rfc_anchor, None)]
        return []

    def resolve_docid(self) -> Optional[DocID]:
        if self.anchor.startswith('IANA.'):
            id = self.anchor.replace('IANA.', 'IANA ', 1).replace('_', '/')
            return DocID(type="IANA", id=id)
        return None


@register_adapter('bibxml9')
class RfcSubseriesAdapter(Xml2rfcAdapter):
    """
    Handles RFC subseries.

    Similarly to RFCs, the logic is fairly straightforward.

    .. note:: :attr:`.SUBSERIES_STEMS` must be updated manually
              should new subseries abbreviations appear.
    """
    exact_docid_match: bool = False

    SUBSERIES_STEMS = set([
        'STD',
        'BCP',
        'FYI',
    ])
    """Exhaustive set of all RFC subseries ID prefixes."""

    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        if ((docid := get_primary_docid(item.docid))
                and docid.type == 'IETF'
                and ' ' in docid.id
                and any([
                    docid.id.startswith(f'{stem} ')
                    for stem in cls.SUBSERIES_STEMS
                ])):
            stem, num = docid.id.split(' ')
            return [(f'{stem}.{num.zfill(4)}', None)]
        return []

    def resolve_docid(self) -> Optional[DocID]:
        parts = self.anchor.split('.')

        if len(parts) >= 2:
            series, num_raw, *_ = self.anchor.split('.')
            try:
                num = int(num_raw)
            except ValueError:
                raise ValueError("Invalid rfcsubseries number component")
            return DocID(type="IETF", id=f"{series} {num}")

        return None


@register_adapter('bibxml-nist')
class NistAdapter(Xml2rfcAdapter):
    """
    Resolves NIST paths.

    This is not very reliable, fallbacks may occur.
    """

    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        if ((docid := get_primary_docid(item.docid))
                and docid.type == "NIST"):
            return [(f"NIST.{docid.id.replace(' ', '_')}", None)]
        return []

    def resolve_docid(self) -> Optional[DocID]:
        # We give up on resolving legacy anchor to docid for NIST,
        # due to inconsistent use of NBS/NIST/etc. prefixes.
        return None

    def fetch_refs(self) -> Sequence[RefData]:
        if self.anchor.startswith('NIST.'):
            docid = (
                self.anchor.
                removeprefix('NIST.').
                replace('_', ' ').replace('.', ' '))

            # Split prefix from the rest
            _, rest = docid.split(' ', 1)

            query = (
                '@.type == "NIST" && ('
                    # Handles e.g. NIST.LCIRC.xxxx,
                    # which should be NIST.NBS.LCIRC
                    '@.id like_regex "(?i)(NBS|NIST) %s" ||'
                    # Handles normal cases like NIST.NBS.xxxx
                    '@.id like_regex "(?i)%s"'
                ')' % (re.escape(rest), re.escape(docid))
            )
            self.log(f"using query {query}")
            return search_refs_relaton_field({
                'docid[*]': query,
            }, limit=10, exact=True)
        return []


@register_adapter('bibxml7')
class DoiAdapter(Xml2rfcAdapter):
    """
    Resolves DOI paths, using Crossref integration.
    """
    @classmethod
    def reverse(cls, item: BibliographicItem) -> List[ReversedRef]:
        if (dois := list(filter(lambda d: d.type == 'DOI', item.docid))):
            return [(f'DOI.{dois[0].id}', None)]
        return []

    def resolve(self) -> BibliographicItem:
        docid = DocID(type='DOI', id=self.anchor.removeprefix('DOI.'))
        result = get_doi_bibitem(docid)
        if not result:
            raise RefNotFoundError()
        else:
            return result.bibitem

    def format_anchor(self) -> Optional[str]:
        formatted_anchor = self.anchor.replace(".", "_", 1).replace("/", "_")
        return f"{formatted_anchor.upper()}"


def _sort_by_id_draft_number(item: RefData):
    """For sorting Internet Drafts."""
    the_id = [
        docid['id']
        for docid in item.body['docid']
        if docid['type'] == 'Internet-Draft'][0]
    return the_id
