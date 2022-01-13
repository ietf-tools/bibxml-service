from typing import List, Dict, Any
from pydantic import ValidationError
from crossref.restful import Works

from common.util import as_list

from bib_models import Link, Title, DocID, BibliographicItem
from bib_models import Contributor, Person, PersonName, PersonAffiliation
from bib_models import Organization, GenericStringValue

from main.types import SourcedBibliographicItem, ExternalSourceMeta


works = Works()


ISBN_TMPL = '{0}{1}{2}-{3}-{4}{5}{6}{7}-{8}{9}{10}{11}-{12}'
ALT_TITLES = [
    'subtitle',
    'original-title',
    'short-title',
    'container-title',
    'short-container-title',
    'group-title',
]


def get_bibitem(doi: str) -> SourcedBibliographicItem:
    """Retrieves DOI information from CrossRef
    and deserializes into a :class:`bib_models.BibliographicItem` instance."""

    resp = works.doi(doi)

    docids: List[DocID] = [DocID(
        type='DOI',
        id=resp['DOI'],
    )]

    docids.extend([
        DocID(
            type='ISSN',
            # We are ignoring issn-type (unclear purpose)
            id=issn)
        for issn in resp.get('ISSN', [])])

    docids.extend([
        DocID(
            type='ISBN',
            # We are ignoring isbn-type
            id=ISBN_TMPL.format(*isbn))
        for isbn in resp.get('ISBN', [])
        if len(isbn) == 13])

    isbn = resp.get('reference', {}).get('isbn')
    if isbn and isbn not in docids:
        docids.append(DocID(type='ISBN', id=isbn))

    contributors = [
        *(to_contributor('author', author)
          for author in resp.get('author', [])),
        *(to_contributor('editor', editor)
          for editor in resp.get('editor', [])),
        *(to_contributor('translator', translator)
          for translator in resp.get('translator', [])),
        *(to_contributor('chair', chair)
          for chair in resp.get('chair', [])),
    ]
    if 'publisher' in resp:
        contributors.append(Contributor(
            role=['publisher'],
            organization=Organization(
                name=resp.get('publisher'),
            ),
        ))

    titles = [
        Title(content=title)
        for title in resp['title']
    ]
    for tid in ALT_TITLES:
        if tid in resp:
            titles.extend([
                Title(content=title, type=tid)
                for title in as_list(resp.get('tid', []))
            ])

    data = dict(
        # The following are not captured:
        # source
        # standards-body
        # institution
        # edition, edition-number, issue, part-number, component-number
        # dates: accepted, content-updated, published-print, approved,
        # indexed, posted, published, published-other, deposited
        # alternative-id
        # publisher, publisher-location
        # type, subtype — need to map to Relaton’s types
        # subject
        # relation, update-to — need to convert to Relaton’s relations
        docid=docids,
        language=resp.get('language', None),
        title=titles,
        link=[Link(
            content=resp['URL'],
        )],
        abstract=[{
            'content': resp['abstract'],
        }] if 'abstract' in resp else [],
        contributor=contributors,
    )

    errors = []

    try:
        BibliographicItem(**data)
    except ValidationError as e:
        errors.append(str(e))

    return SourcedBibliographicItem(
        **data,
        sources={
            'doi': ExternalSourceMeta(
                bibitem=resp,
                validation_errors=errors,
                requests=[],
            ),
        },
    )


def to_contributor(role: str, crossref_author: Dict[str, Any]) -> Contributor:
    return Contributor(
        role=[role],
        person=Person(
            affiliation=[PersonAffiliation(
                organization=Organization(
                    name=[aff['name']],
                ),
            ) for aff in crossref_author['affiliation']],
            name=PersonName(
                surname=GenericStringValue(
                    content=crossref_author['family'],
                ),
                completename=GenericStringValue(
                    content=crossref_author['name'],
                ) if 'name' in crossref_author else None,
                forename=GenericStringValue(
                    content=crossref_author['given'],
                ) if 'given' in crossref_author else None,
            ),
        ),
    )
