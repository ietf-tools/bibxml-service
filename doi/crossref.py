"""Responsible for Crossref interaction."""

from typing import List, Dict, Any

from crossref.restful import Works, Etiquette
from django.conf import settings
from pydantic import ValidationError
from relaton.models.bibdata import Locality, LocalityStack

from bib_models import DocID, BibliographicItem
from bib_models import GenericStringValue, Link
from bib_models import Person, PersonAffiliation, PersonName
from bib_models import Title, Contributor, Organization
from common.util import as_list
from main.exceptions import RefNotFoundError
from main.types import ExternalBibliographicItem, ExternalSourceMeta

etiquette = Etiquette(
    settings.SERVICE_NAME,
    settings.SNAPSHOT,
    settings.HOSTNAME,
    settings.ADMINS[0][1],
)
"""Etiquette info to be used when making Crossref API requests."""

works = Works(etiquette=etiquette)


def get_bibitem(docid: DocID, strict: bool = True) \
        -> ExternalBibliographicItem:
    """Retrieves DOI information from Crossref and deserializes it
    into a :class:`main.types.ExternalBibliographicItem` instance.

    :param str docid: DOI identifier
    :param bool strict: see :ref:`strict-validation`
    :returns None: if no match was returned by Crossref
    :rtype: None or main.types.ExternalBibliographicItem
    :raises ValueError: wrong docid.type (not DOI)
    :raises main.exceptions.RefNotFoundError: no matching item returned
    :raises pydantic.ValidationError:
        strict is True and Relaton data failed to validate
    """

    if docid.type != 'DOI':
        raise ValueError(
            "DOI source requires DOI docid.type",
            repr(docid))

    resp = works.doi(docid.id)

    if not resp:
        raise RefNotFoundError()

    docids: List[DocID] = [
        DocID(type='DOI', id=resp['DOI']),

        *(DocID(type='ISSN', id=issn)
          for issn in resp.get('ISSN', [])),

        *(DocID(type='ISBN', id=ISBN_TMPL.format(*isbn))
          for isbn in resp.get('ISBN', [])
          if len(isbn) == 13),
    ]

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

    # LocalityStack
    ct = resp.get('container-title')
    if ct:
        volume = resp.get('volume', None)
        issue = resp.get('journal-issue', {}).get("issue")
        page = resp.get('page', None)
        localities = [{"type": "container-title", "value": ct[0]}]
        if volume:
            localities.append({"type": "volume", "value": volume})
        if issue:
            localities.append({"type": "issue", "value": issue})
        if volume:
            localities.append({"type": "page", "value": page})

        extent: LocalityStack = LocalityStack(locality=[
            Locality(type=locality.get("type"), reference_from=locality.get("value"))
            for locality in localities
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
            'format': 'application/x-jats+xml',  # See GitHub issue 210
        }] if 'abstract' in resp else [],
        contributor=contributors,
        extent=extent
    )

    errors = []
    if strict:
        bibitem = BibliographicItem(**data)
    else:
        try:
            bibitem = BibliographicItem(**data)
        except ValidationError as e:
            errors.append(str(e))
            bibitem = BibliographicItem.construct(**data)

    return ExternalBibliographicItem(
        source=ExternalSourceMeta(
            id='crossref-api',
            home_url="http://api.crossref.org",
        ),
        bibitem=bibitem,
        validation_errors=errors,
        requests=[],
    )


def to_contributor(role: str, crossref_author: Dict[str, Any]) \
        -> Contributor:
    """Constructs a contributor from the author object
    returned by Crossref.

    :param str role: contributor’s role
    :param dict crossref_author: structure from Crossref response
    :rtype: relaton.models.bibdata.Contributor
    """
    return Contributor(
        role=[role],
        person=Person(
            affiliation=[PersonAffiliation(
                organization=Organization(
                    # NOTE: DOI seems to supply abbreviation as name.
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


ISBN_TMPL = '{0}{1}{2}-{3}-{4}{5}{6}{7}-{8}{9}{10}{11}-{12}'
"""Crossref returns ISBNs without dashes.
This format string conforms it to Relaton, which uses dashes."""

ALT_TITLES = [
    'subtitle',
    'original-title',
    'short-title',
    'container-title',
    'short-container-title',
    'group-title',
]
