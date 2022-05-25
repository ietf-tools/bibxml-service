"""Functions responsible for retrieving bibliographic items
from xml2rfc anchors (in other words, resolving /public/rfc/... paths).
See :term:`xml2rfc fetcher`.

Plug registered fetchers into root URL configuration
via :func:`.urls.get_urls()`.
"""

import logging
from typing import cast, Optional, Match
import re

from pydantic import ValidationError

from bib_models import BibliographicItem, DocID
from doi.crossref import get_bibitem as get_doi_bibitem
from datatracker.internet_drafts import get_internet_draft
from datatracker.internet_drafts import remove_version
from datatracker.internet_drafts import version_re
from common.util import as_list
from main.models import RefData
from main.query import search_refs_relaton_field
from main.exceptions import RefNotFoundError

from .urls import register_fetcher


log = logging.getLogger(__name__)


@register_fetcher('bibxml')
def rfcs(ref: str) -> BibliographicItem:
    rfc_anchor_docid = ref.replace('.', '')

    results = search_refs_relaton_field({
        'docid[*]':
            '@.type == "IETF" && '
            '@.scope == "anchor" && '
            '@.id == "%s"'
        % re.escape(rfc_anchor_docid),
    }, limit=10, exact=True)

    if len(results) > 0:
        return BibliographicItem(**results[0].body)
    else:
        raise RefNotFoundError()


@register_fetcher('bibxml2')
def misc(ref: str) -> BibliographicItem:
    results = search_refs_relaton_field({
        'docid[*]': '@.id == "%s"'
        % re.escape(ref),
    }, limit=10, exact=True)

    if len(results) > 0:
        return BibliographicItem(**results[0].body)
    else:
        raise RefNotFoundError()


@register_fetcher('bibxml3')
def internet_drafts(ref: str) -> BibliographicItem:
    """Returns either latest indexed version,
    or latest version at Datatracker if it’s newer.

    .. note:: Datatracker structures may contain less data than indexed sources.

    Paths should work as follows:

    - Unversioned I-D has path pattern: reference.I-D.xxx.xml
    - Versioned I-D has path pattern: reference.I-D.draft-xxx-nn.xml

    In the following cases, the path should return 404:

    - Unversioned I-D has path pattern: reference.I-D.draft-xxx.xml
    - Versioned I-D has path pattern: reference.I-D.xxx-nn.xml

    (Note that ``ref`` passed to this function, like any other fetcher,
    already excludes the ``reference.`` prefix.)

    .. seealso:: :issue:`157`
    """
    bare_ref = ref.replace('I-D.', '', 1).replace('draft-', '', 1)
    unversioned_ref, requested_version = remove_version(bare_ref)

    ref_is_valid = all([
        # all references must have the I-D. prefix:
        ref.startswith('I-D.'),
        any([
            # and must be either versioned with the additional draft- prefix:
            ref.startswith('I-D.draft-') and requested_version,
            # or unversioned without the additional draft- prefix:
            not ref.startswith('I-D.draft-') and not requested_version,
        ]),
    ])
    if not ref_is_valid:
        raise RefNotFoundError(
            "unsupported xml2rfc-style I-D reference: "
            "possibly missing I-D prefix "
            "or unexpected draft- prefix and trailing version combination")

    # Look up by primary identifier
    if requested_version:
        docid_variants = [f'draft-{unversioned_ref}-{requested_version}']
    else:
        docid_variants = [f'draft-{unversioned_ref}']
    id_query = ' || '.join([
        '@.id == "%s"' % variant
        for variant in docid_variants
    ])
    results = sorted(
        search_refs_relaton_field({
            'docid[*]': f'(@.type == "Internet-Draft") && ({id_query})',
        }, limit=10, exact=True),
        key=_sort_by_id_draft_number,
        reverse=True,
    )

    # Obtain the newest draft version available in indexed sources
    # (both bibitem data and version number)
    indexed_bibitem: Optional[BibliographicItem]
    indexed_version: Optional[str]
    if len(results) > 0:
        # We should catch (but log) a ValidationError here,
        # making sure xml2rfc API consumers receive a suitable response
        # whenever possible.
        try:
            indexed_bibitem = BibliographicItem(**results[0].body)
            try:
                match = [
                    version_re.match(d.id)
                    for d in as_list(indexed_bibitem.docid or [])
                    if d.type == 'Internet-Draft'
                ][0]
            except IndexError:
                indexed_version = None
            else:
                indexed_version = match.group('version') if match else None
        except ValidationError:
            log.exception(
                "Failed to validate indexed bibliographic item "
                "when resolving xml2rfc bibxml3")
            indexed_bibitem = None
            indexed_version = None
    else:
        indexed_bibitem = None
        indexed_version = None

    # Check Datatracker’s latest version (slow)
    try:
        dt_bibitem = get_internet_draft(
            f'draft-{bare_ref}',
            strict=indexed_bibitem is None,
        ).bibitem
        dt_version = dt_bibitem.edition.content

        if not isinstance(dt_version, str):
            raise ValueError(
                f"Malformed I-D version (not a string): "
                f"{dt_version}")
        try:
            parsed_version = int(dt_version)
        except (ValueError, TypeError):
            raise ValueError(
                f"Malformed I-D version (doesn’t parse to an integer): "
                f"{dt_version}")
        else:
            if parsed_version < 0:
                raise ValueError(
                    f"Malformed I-D version (not a positive integer): "
                    f"{dt_version}")

    except:
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
            not requested_version,
            # We were requested a version and we got that version from Datatracker
            requested_version == dt_version,
        ]) and any([
            # We did not find indexed item matching given ID and maybe version:
            not indexed_bibitem,
            # We were not requested a version,
            # and latest version on Datatracker is different (assuming newer):
            not requested_version and indexed_version != dt_version,
            # We were requested a version,
            # and somehow indexed version does not match requested version:
            requested_version and indexed_version != requested_version,
        ]):
            # Datatracker’s version is newer or we don’t have this draft indexed.
            # Note this (should be transient until sources are reindexed, if not
            # then there’s a problem) and return Datatracker’s version
            log.warn(
                "Returning Datatracker result for xml2rfc bibxml3 path. "
                "If unversioned I-D was requested, "
                "then Datatracker may have a newer I-D version than indexed sources. "
                "Alternatively, indexed version could not be used for some reason. "
                "Requested version %s, "
                "indexed sources have version %s, "
                "returning Datatracker’s version %s. ",
                requested_version,
                dt_version,
                indexed_version)
            return dt_bibitem

    if indexed_bibitem and any([
        not requested_version,
        indexed_version == requested_version,
    ]):
        return indexed_bibitem
    else:
        raise RefNotFoundError()


@register_fetcher('bibxml4')
def w3c(ref: str) -> BibliographicItem:
    docid = ref.replace('W3C.', 'W3C ')

    results = search_refs_relaton_field({
        'docid[*]': '@.type == "W3C" && @.id == "%s"'
        % re.escape(docid),
    }, limit=10, exact=True)

    if len(results) > 0:
        return BibliographicItem(**results[0].body)
    else:
        raise RefNotFoundError()


@register_fetcher('bibxml5')
def threegpp(ref: str) -> BibliographicItem:
    docid = ref.replace('SDO-3GPP.', '').replace('3GPP.', '')

    results = search_refs_relaton_field({
        'docid[*]': '@.type == "3GPP" && @.id like_regex "%s"'
        % re.escape(docid),
    }, limit=10, exact=True)

    if len(results) > 0:
        return BibliographicItem(**results[0].body)
    else:
        raise RefNotFoundError()


@register_fetcher('bibxml6')
def ieee(ref: str) -> BibliographicItem:
    rough_docid = ref.replace('.', ' ').replace('-', ' ').replace('_', ' ')
    parts = rough_docid.split(' ')
    regex = '.*'.join(parts)

    results = search_refs_relaton_field({
        'docid[*]': '@.type == "IEEE" && @.id like_regex "(?i)%s"'
        % re.escape(regex),
    }, limit=10, exact=True)

    if len(results) > 0:
        return BibliographicItem(**results[0].body)
    else:
        raise RefNotFoundError()


@register_fetcher('bibxml7')
def doi(ref: str) -> BibliographicItem:
    docid = DocID(type='DOI', id=ref)
    result = get_doi_bibitem(docid)
    if not result:
        raise RefNotFoundError()
    else:
        return result.bibitem


@register_fetcher('bibxml8')
def iana(ref: str) -> BibliographicItem:
    results = search_refs_relaton_field({
        'docid[*]': '@.type == "IANA" && @.id like_regex "(?i)%s"'
        % re.escape(ref.replace('IANA.', '')),
    }, limit=10, exact=True)
    if len(results) > 0:
        return BibliographicItem(**results[0].body)
    else:
        raise RefNotFoundError()


@register_fetcher('bibxml9')
def rfcsubseries(ref: str) -> BibliographicItem:
    parts = ref.split('.')

    if len(parts) >= 2:
        series, num_raw, *_ = ref.split('.')

        try:
            num = int(num_raw)
        except ValueError:
            raise RefNotFoundError("Invalid rfcsubseries number component")

        results = search_refs_relaton_field({
            'docid[*]': '@.type == "IETF" && (@.id == "%s" || @.id == "%s")'
            % (f'{series}{num}', f'{series} {num}'),
        }, limit=10, exact=True)

        if len(results) > 0:
            return BibliographicItem(**results[0].body)

    raise RefNotFoundError()


@register_fetcher('bibxml-nist')
def nist(ref: str) -> BibliographicItem:
    results = search_refs_relaton_field({
        'docid[*]': '@.id == "%s" && @.type == "NIST"'
        % re.escape(ref.replace('.', ' ')),
    }, limit=10, exact=True)

    if len(results) > 0:
        return BibliographicItem(**results[0].body)
    else:
        raise RefNotFoundError()


def _sort_by_id_draft_number(item: RefData):
    """For sorting Internet Drafts."""
    the_id = [
        docid['id']
        for docid in item.body['docid']
        if docid['type'] == 'Internet-Draft'][0]
    return the_id
