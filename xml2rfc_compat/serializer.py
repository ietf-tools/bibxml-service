"""Utilities for converting :class:`bib_models.models.BibliographicItem`
to BibXML/xml2rfc per RFC 7991.

Conversion is very lossy.

Primary API are :func:`to_xml()` and :func:`to_xml_string()`.
"""

import datetime
from typing import List, Optional, Union, Callable, Tuple, Set
from xml.etree.ElementTree import Element

from lxml import etree, objectify

from bib_models.models import BibliographicItem, Relation, Series, parse_relaxed_date
from bib_models.dataclasses import Contributor, PersonAffiliation, Organization
from bib_models.dataclasses import GenericStringValue, Contact, DocID

from common.util import as_list


E = objectify.E


AUTHOR_ROLES = set(('author', 'editor'))


__all__ = (
    'to_xml',
    'to_xml_string',
)


def to_xml_string(item: BibliographicItem, **kwargs) -> str:
    """
    Passes given item through ``to_xml()``
    and renders it to a string with pretty print.

    All kwargs are passed to ``to_xml()``.
    """
    return etree.tostring(to_xml(item, **kwargs), pretty_print=True)


def to_xml(item: BibliographicItem, anchor=None) -> Element:
    """Converts a BibliographicItem to XML,
    trying to follow RFC 7991.

    Returned root element is either a ``<reference>``
    or a ``<referencegroup>``.

    :param str anchor: resulting root element ``anchor`` property.

    :raises ValueError: if there are different issues
                        with given item’s structure
                        that make it unrenderable per RFC 7991.
    """

    titles = as_list(item.title or [])
    relations: List[Relation] = as_list(item.relation or [])

    constituents = [rel for rel in relations if rel.type == 'includes']

    is_referencegroup = len(titles) < 1 and len(constituents) > 0
    is_reference = len(titles) > 0

    if is_reference:
        root = create_reference(item)

    elif is_referencegroup:
        root = create_referencegroup([
            ref.bibitem
            for ref in constituents])

    else:
        raise ValueError(
            "Able to construct neither <reference> nor <referencegroup>: "
            "impossible combination of titles and relations")

    if anchor:
        root.set('anchor', anchor)

    objectify.deannotate(root)
    etree.cleanup_namespaces(root)

    return root


# References and reference groups
# ===============================

def create_referencegroup(items: List[BibliographicItem]) -> Element:
    return E.referencegroup(*(
        create_reference(item)
        for item in items
    ))


def create_reference(item: BibliographicItem) -> Element:
    titles = as_list(item.title or [])
    if len(titles) < 1:
        raise ValueError("Unable to create a <reference>: no titles")

    contributors: List[Contributor] = as_list(item.contributor or [])
    author_contributors: List[Contributor] = [
        contrib
        for contrib in contributors
        if is_author(contrib)
    ]

    front = E.front(
        E.title(titles[0].content),
        *(create_author(contrib) for contrib in author_contributors),
    )

    published_date: Optional[datetime.date] = None
    specificity: Optional[str] = None
    for date in as_list(item.date or []):
        if date.type == 'published':
            if isinstance(date.value, str):
                relaxed = parse_relaxed_date(date.value)
                if relaxed:
                    published_date = relaxed[0]
                    specificity = relaxed[2]
            else:
                published_date = date.value
                specificity = 'day'
            break
    if published_date and specificity:
        date_el = E.date(year=published_date.strftime('%Y'))
        if specificity in ['month', 'day']:
            date_el.set('month', published_date.strftime('%B'))
        if specificity == 'day':
            date_el.set('day', str(published_date.day))
        front.append(date_el)

    abstracts = as_list(item.abstract or [])
    if len(abstracts) > 0:
        front.append(E.abstract(*(
            E.t(p)
            for p in get_paragraphs(abstracts[0].content)
        )))

    ref = E.reference(front)

    links = as_list(item.link or [])
    if len(links) > 0:
        ref.set('target', links[0].content)

    docids: List[DocID] = as_list(item.docid or [])
    series: Set[Union[None, Tuple[str, str]]] = set()
    for docid in docids:
        series = series | set([
            func(docid)
            for func in DOCID_SERIES_EXTRACTORS
        ])
    series_: List[Series] = as_list(item.series or [])
    series = series | set([
        (as_list(s.title)[0].content, s.number)
        for s in series_
        if s.number and s.title
    ])
    for series_info in series:
        if series_info is not None:
            ref.append(E.seriesInfo(
                name=series_info[0],
                value=series_info[1],
            ))

    return ref


# Authors and contributors
# ========================

is_author = (
    lambda contrib:
    len(set(as_list(contrib.role)) & AUTHOR_ROLES) > 0
)


def create_author(contributor: Contributor) -> Element:
    if not is_author(contributor):
        raise ValueError(
            "Unable to construct <author>: incompatible roles")

    if not contributor.organization and not contributor.person:
        raise ValueError(
            "Unable to construct <author>: "
            "neither an organization nor a person")

    author_el = E.author()

    roles = as_list(contributor.role)

    if 'editor' in roles:
        author_el.set('role', 'editor')

    org: Optional[Organization] = None
    if contributor.organization:
        org = contributor.organization
    elif contributor.person:
        affiliations: List[PersonAffiliation] = \
            as_list(contributor.person.affiliation or [])
        if len(affiliations) > 0:
            org = affiliations[0].organization
        else:
            org = None

    if org is not None:
        # Organization
        org_el = E.organization(as_list(org.name)[0])

        if org.abbreviation:
            org_el.set('abbrev', org.abbreviation)

        author_el.append(org_el)

        # Address & postal
        contacts: List[Contact] = as_list(org.contact or [])
        postal_contacts = [
            c for c in contacts
            if c.country
        ]
        if len(postal_contacts) > 0 or org.url:
            addr = E.address()

            if len(postal_contacts) > 0:
                contact = postal_contacts[0]
                postal = E.postal(
                    E.country(contact.country)
                )
                if contact.city:
                    postal.append(E.city(contact.city))
                addr.append(postal)

            if org.url:
                addr.append(E.uri(org.url))

            author_el.append(addr)

    if contributor.person:
        name = contributor.person.name
        if name.completename:
            author_el.set('fullname', name.completename.content)
        if name.surname:
            author_el.set('surname', name.surname.content)
        if name.initial:
            initials: List[GenericStringValue] = \
                as_list(name.initial or [])
            author_el.set('initials', ' '.join([
                i.content.replace('.', ' ').strip()
                for i in initials
            ]))

    return author_el


# Extracting seriesInfo from docid
# ================================

# According to idiomatic conventions observed in xml2rfc data.

def extract_doi_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'doi':
        return 'DOI', docid.id
    return None


def extract_rfc_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'ietf' and docid.id.lower().startswith('rfc '):
        return 'RFC', docid.id.replace('.', ' ').split(' ')[-1]
    return None


def extract_id_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'internet-draft':
        return 'Internet-Draft', docid.id
    return None


def extract_w3c_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'w3c':
        return 'W3C', docid.id.replace('.', ' ').split('W3C ')[-1]
    return None


def extract_3gpp_tr_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == '3gpp':
        ver = docid.id.split('/')[-1]
        id = docid.id.split('3GPP TR ')[1].split(':')[0]
        return '3GPP TR', f'{id} {ver}'
    return None


def extract_ieee_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'ieee':
        id, year = docid.id.replace('IEEE ', ' ').lower().strip().split('.')
        return 'IEEE', '%s-%s' % (id.replace('-', '.'), year)
    return None


DOCID_SERIES_EXTRACTORS: List[
    Callable[[DocID], Union[Tuple[str, str], None]]
] = [
    extract_doi_series,
    extract_rfc_series,
    extract_id_series,
    extract_w3c_series,
    extract_3gpp_tr_series,
    extract_ieee_series,
]


# Extracting text from maybe-HTML abstracts
# =========================================

def get_paragraphs(val: str) -> List[str]:
    try:
        return get_paragraphs_html(val)
    except (etree.XMLSyntaxError, ValueError):
        return get_paragraphs_plain(val)


def get_paragraphs_html(val: str) -> List[str]:
    tree = etree.fromstring(f'<main>{val}</main>')
    ps = [
        p.text for p in tree.findall('p')
        if (getattr(p, 'text', '') or '') != ''
    ]
    if len(ps) > 0:
        return ps
    else:
        raise ValueError("No HTML text detected")


def get_paragraphs_plain(val: str) -> List[str]:
    return [
        p.strip()
        for p in val.split('\n')
        if p.strip() != ''
    ]
