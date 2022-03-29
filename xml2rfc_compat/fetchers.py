"""Functions responsible for retrieving bibliographic items
from xml2rfc anchors. See :term:`xml2rfc fetcher`.

Plug registered fetchers into root URL configuration
via :func:`.urls.get_urls()`.
"""

import logging
from typing import cast, Union
import re

from bib_models.models.bibdata import BibliographicItem, DocID
from doi.crossref import get_bibitem as get_doi_bibitem
from datatracker.internet_drafts import get_internet_draft, remove_version
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
    """
    type_query = '@.type == "Internet-Draft" || @.type == "IETF"'

    bare_ref = ref.replace('I-D.', '', 1).replace('draft-', '', 1)

    if bare_ref != remove_version(bare_ref):
        raise RefNotFoundError("Versioned I-D references are not supported")

    draft_prefixed = f'draft-{bare_ref}'

    # Look up by ID using variants with/without draft- and I-D. prefixes
    prefix_variants = [
        bare_ref,
        draft_prefixed,
        f'I-D.{bare_ref}',
    ]
    id_query = ' || '.join([
        '@.id == "%s"' % variant
        for variant in prefix_variants
    ])

    results = sorted(
        search_refs_relaton_field({
            'docid[*]': f'({type_query}) && ({id_query})',
        }, limit=10, exact=True),
        key=_sort_by_id_draft_number,
        reverse=True,
    )

    # Obtain the newest draft version available in indexed sources
    # (both bibitem data and version number)
    bibitem: Union[BibliographicItem, None]
    if len(results) > 0:
        bibitem = BibliographicItem(**results[0].body)
        try:
            version = [
                version_re.match(d.id).group('version')
                for d in as_list(bibitem.docid or [])
                if d.type == 'Internet-Draft' and version_re.match(d.id)
            ][0]
        except:
            version = None

    else:
        bibitem = None
        version = None

    # Check Datatracker’s latest version (slow)
    try:
        dt_bibitem = get_internet_draft(
            f'draft-{bare_ref}',
            strict=bibitem is None,
        ).bibitem
        dt_version = dt_bibitem.edition.content
    except:
        log.exception(
            "Failed to fetch or validate latest draft from Datatracker "
            "when resolving xml2rfc bibxml3 path")
    else:
        if not version or version != dt_version:
            # Datatracker’s version is newer or we don’t have this draft indexed.
            # Note this (should be transient until sources are reindexed, if not
            # then there’s a problem) and return Datatracker’s version
            log.warn(
                "Datatracker has newer I-D version %s "
                "(indexed sources have %s), "
                "returning Datatracker’s version",
                dt_version,
                version)
            return dt_bibitem

    if bibitem:
        return bibitem
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
        series, num, *_ = ref.split('.')
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
        % re.escape(ref),
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
