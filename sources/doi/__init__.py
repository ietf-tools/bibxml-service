from typing import List, Dict, Any, Union

from pydantic import ValidationError
from crossref.restful import Works, Etiquette

from django.conf import settings

from common.util import as_list

from bib_models.dataclasses import DocID, Title, Contributor, Organization
from bib_models.dataclasses import Person, PersonAffiliation, PersonName
from bib_models.dataclasses import GenericStringValue
from bib_models.models import BibliographicItem, Link

from main.types import ExternalBibliographicItem, ExternalSourceMeta
from main.exceptions import RefNotFoundError


etiquette = Etiquette(
    settings.SERVICE_NAME,
    settings.SNAPSHOT,
    settings.HOSTNAME,
    settings.ADMINS[0][1],
)
works = Works(etiquette=etiquette)


ISBN_TMPL = '{0}{1}{2}-{3}-{4}{5}{6}{7}-{8}{9}{10}{11}-{12}'
ALT_TITLES = [
    'subtitle',
    'original-title',
    'short-title',
    'container-title',
    'short-container-title',
    'group-title',
]


def get_bibitem(docid: DocID) \
        -> Union[ExternalBibliographicItem, None]:
    """Retrieves DOI information from CrossRef
    and deserializes into a :class:`bib_models.BibliographicItem` instance."""

    if docid.type != 'DOI':
        raise RefNotFoundError(
            "DOI source requires DOI docid.type",
            repr(docid))

    resp = works.doi(docid.id)

    if not resp:
        return None

    docids: List[DocID] = [
        DocID(type='DOI', id=resp['DOI']),

        *(DocID(type='ISSN', id=issn)
          for issn in resp.get('ISSN', [])),

        *(DocID(type='ISBN', id=ISBN_TMPL.format(*isbn))
          for isbn in resp.get('ISBN', [])
          if len(isbn) == 13),
    ]
    isbn = resp.get('reference', {}).get('isbn')
    if isbn and isbn not in docids:
        docids.append(DocID(
            type='ISBN',
            id=isbn,
        ))

    contributors: List[Contributor] = [
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

    titles: List[Title] = [
        *(Title(content=title, type=None)
          for title in resp['title']),

        *(Title(content=title, type=tid)
          for tid in ALT_TITLES
          for title in as_list(resp.get(tid, []))
          if tid in resp),
    ]

    data = dict(
        # The following are not captured:
        # source
        # standards-body
        # institution
        # edition, edition-number, issue, part-number, component-number
        # dates: accepted, content-updated, published-print, approved,
        # indexed, posted, published, published-other, deposited
        # alternative-id
        # isbn-type, issn-type
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
        bibitem = BibliographicItem(**data)
    except ValidationError as e:
        errors.append(str(e))
        bibitem = BibliographicItem.construct(**data)

    return ExternalBibliographicItem(
        source=ExternalSourceMeta(
            id='crossref-doi',
        ),
        bibitem=bibitem,
        validation_errors=errors,
        requests=[],
    )


def to_contributor(role: str, crossref_author: Dict[str, Any]) \
        -> Contributor:
    return Contributor(
        role=[role],
        person=Person(
            affiliation=[PersonAffiliation(
                organization=Organization(
                    name=[aff['name']],
                    contact=[],
                    url=None,
                    abbreviation=None,
                ),
            ) for aff in crossref_author['affiliation']],
            name=PersonName(
                surname=GenericStringValue(
                    content=crossref_author['family'],
                ) if 'family' in crossref_author else None,
                completename=GenericStringValue(
                    content=crossref_author['name'],
                ) if 'name' in crossref_author else None,
                forename=[GenericStringValue(
                    content=crossref_author['given'],
                )] if 'given' in crossref_author else [],
            ),
        ),
    )
