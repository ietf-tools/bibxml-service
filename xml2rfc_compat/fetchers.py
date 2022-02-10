"""Functions responsible for retrieving bibliographic items
from xml2rfc anchors.

Plug these functions into root URL configuration
via :func:`urls.make_xml2rfc_path_pattern`.
"""

import re

from bib_models.models import BibliographicItem
from bib_models.dataclasses import DocID
from sources.exceptions import RefNotFoundError
from doi.crossref import get_bibitem as get_doi_bibitem
from main.models import RefData
from main.query import search_refs_relaton_field

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
    # E.g., draft-abarth-cookie-07
    option1 = (
        '@.type == "Internet-Draft" && @.id == "%s"'
        % ref.replace('I-D.', ''))
    # E.g., draft-abarth-cookie
    option2 = (
        r'@.type == "Internet-Draft" && @.id like_regex "%s\-\d{2}"'
        % ref.replace('I-D.', ''))
    # E.g., I-D.abarth-cookie
    option3 = (
        '@.type == "IETF" && @.id == "%s"'
        % ref)

    results = sorted(
        search_refs_relaton_field({
            'docid[*]': ' || '.join([
                f'({opt})'
                for opt in [option1, option2, option3]
            ]),
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
