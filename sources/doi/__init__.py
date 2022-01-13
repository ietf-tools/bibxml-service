from typing import List, Dict, Any
from pydantic import ValidationError
from crossref.restful import Works

from bib_models import Link, Title, DocID, BibliographicItem
from bib_models import Contributor, Person, PersonName, PersonAffiliation
from bib_models import Organization

from main.types import SourcedBibliographicItem, ExternalSourceMeta


works = Works()


def get_bibitem(doi: str) -> SourcedBibliographicItem:
    """Retrieves DOI information from CrossRef
    and deserializes into a :class:`bib_models.BibliographicItem` instance."""

    resp = works.doi(doi)

    docids: List[DocID] = [DocID(
        type='DOI',
        id=resp['DOI'],
    )]

    docids.extend([DocID(
        type='ISSN',
        # We are ignoring issn-type (unclear purpose)
        id=issn,
    ) for issn in resp.get('ISSN', [])])

    docids.extend([DocID(
        type='ISBN',
        # We are ignoring isbn-type
        id=isbn,
    ) for isbn in resp.get('ISBN', [])])

    isbn = resp.get('reference', {}).get('isbn')
    if isbn and isbn not in docids:
        docids.append(DocID(type='ISBN', id=isbn))

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
        title=[Title(
            # We are ignoring subtitle, original-title, short-title,
            # container-title, short-container-title, group-title
            content=title,
        ) for title in resp['title']],
        link=[Link(
            content=resp['URL'],
        )],
        contributor=[
            *(to_contributor('author', author)
              for author in resp.get('author', [])),
            *(to_contributor('editor', editor)
              for editor in resp.get('editor', [])),
            *(to_contributor('translator', translator)
              for translator in resp.get('translator', [])),
            *(to_contributor('chair', chair)
              for chair in resp.get('chair', [])),
        ],
    )

    errors = []

    try:
        item = BibliographicItem(**data)
    except ValidationError as e:
        item = BibliographicItem.construct(**data)
        errors.append(str(e))

    return SourcedBibliographicItem(
        **data,
        sources={
            'doi': ExternalSourceMeta(
                bibitem=item,
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
                surname=crossref_author['family'],
                completename=crossref_author.get('name', None),
            ),
        ),
    )
