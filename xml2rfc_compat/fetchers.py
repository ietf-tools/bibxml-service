"""Functions responsible for retrieving bibliographic items
from xml2rfc anchors. See :term:`xml2rfc fetcher`.

Plug registered fetchers into root URL configuration
via :func:`.urls.get_urls()`.
"""

import re

from bib_models.models.bibdata import BibliographicItem, DocID
from doi.crossref import get_bibitem as get_doi_bibitem
from main.models import RefData
from main.query import search_refs_relaton_field
from main.exceptions import RefNotFoundError

from .urls import register_fetcher


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
    type_query = '@.type == "Internet-Draft" || @.type == "IETF"'

    ref_without_prefixes = ref.replace('I-D.', '', 1).replace('draft-', '', 1)
    bare_ref = remove_version(ref_without_prefixes)

    # Variants with/without draft- and I-D. prefixes
    versionless_prefix_variants = [
        bare_ref,
        f'draft-{bare_ref}',
        f'I-D.draft-{bare_ref}',
    ]
    id_query = ' || '.join([
        # Variants with/without version
        '@.id == "%s" || @.id like_regex "%s"' % (
            versionless,
            re.escape(r'%s-\d{2}' % versionless),
        )
        for versionless in versionless_prefix_variants
    ])

    results = sorted(
        search_refs_relaton_field({
            'docid[*]': f'({type_query}) && ({id_query})',
        }, limit=10, exact=True),
        key=_sort_by_id_draft_number,
        reverse=True,
    )

    if len(results) > 0:
        return BibliographicItem(**results[0].body)
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
    series, num = ref.split('.')
    results = search_refs_relaton_field({
        'docid[*]': '@.type == "IETF" && @.id == "%s"'
        % f'{series}{num}',
    }, limit=10, exact=True)
    if len(results) > 0:
        return BibliographicItem(**results[0].body)
    else:
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
