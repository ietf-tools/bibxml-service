"""Retrieving Internet Drafts from Datatracker.

Registers :func:`.get_internet_draft()`
as an :term:`external source` of bibliographic data
for “Internet-Draft” document identifier type.
"""

import ast
from typing import Dict, Any, List
import datetime
import re
import json

import requests
from pydantic import ValidationError

from bib_models.models.bibdata import DocID, BibliographicItem
from main.types import ExternalBibliographicItem, ExternalSourceMeta
from main.exceptions import RefNotFoundError
from main import external_sources

from .request import get, BASE_DOMAIN


__all__ = (
    'get_internet_draft',
    'remove_version',
    'version_re',
)


version_re = re.compile(r'^(?P<versionless>[-\w]+?)(\-(?P<version>\d{2}))?$')
"""A regular expression that allows extracting
a version or a versionless name from an Internet Draft name
that possibly has version."""


def remove_version(id: str) -> str:
    """Removes version suffix from an Internet Draft ID."""

    match = version_re.match(id)

    if not match or not match.group('versionless'):
        raise ValueError("Invalid Datatracker ID: %s" % id)

    return match.group('versionless')


@external_sources.register_for_types('datatracker', {'Internet-Draft': True})
def get_internet_draft(docid: str, strict: bool = True) -> ExternalBibliographicItem:
    """Retrieves an Internet Draft from Datatracker in Relaton format.

    Makes necessary requests to Datatracker API
    and converts .

    :param str docid:
    :param bool strict: see :ref:`strict-validation`
    :rtype: main.types.ExternalBibliographicItem
    """

    versionless = remove_version(docid)

    resp = get(f'api/v1/doc/document/{versionless}/')

    if resp.status_code == 404:
        raise RefNotFoundError()

    data = resp.json()

    bibitem_data: Dict[str, Any] = dict(
        type='draft',
        abstract=[{
            'content': data['abstract'],  # .replace('\n', ' '),
        }] if 'abstract' in data else None,
        edition={
            'content': data['rev'],
        },
        link=[{
            'content': f'{BASE_DOMAIN}%s' % data['resource_uri'],
        }],
        docid=[{
            'type': 'IETF',
            'id': "I-D %s" % data['name'],
            'primary': True,
        }, {
            'type': 'Internet-Draft',
            'id': "%s-%s" % (data['name'], data['rev']),
        }],
        title=[{
            'type': 'main',
            'content': data['title'],
        }],
        fetched=datetime.datetime.now(),
        contributor=[{
            'role': ['publisher'],
            'organization': {
                'name': ['IETF'],
                'abbreviation': 'IETF',
                'url': 'https://ietf.org/'
            },
        }],
    )

    # Some data (e.g., authors and dates) is only available
    # via separate submission endpoint
    latest_submission_url = data['submissions'][-1]
    try:
        latest_submission_data = get(latest_submission_url).json()
    except requests.exceptions.ConnectionError:
        pass
    else:
        if 'document_date' in latest_submission_data:
            bibitem_data['date'] = [{
                'type': 'created',
                'value': latest_submission_data['document_date'],
            }, {
                'type': 'submitted',
                'value': latest_submission_data['submission_date'],
            }]

        if 'authors' in latest_submission_data:
            authors: List[Any]
            if isinstance(latest_submission_data['authors'], list):
                authors = latest_submission_data['authors']
            elif isinstance(latest_submission_data['authors'], str):
                try:
                    authors = json.loads(latest_submission_data['authors'])
                except json.JSONDecodeError:
                    try:
                        authors = ast.literal_eval(latest_submission_data['authors'])
                    except:
                        authors = []
            else:
                authors = []
            if authors:
                bibitem_data['contributor'] += [
                    {
                        'role': ['author'],
                        'person': {'name': {'completename':
                            {'content': a['name']}
                        }},
                    }
                    for a in authors
                ]

    errors: List[str] = []
    if strict:
        bibitem = BibliographicItem(**bibitem_data)
    else:
        try:
            bibitem = BibliographicItem(**bibitem_data)
        except ValidationError as err:
            errors.append(str(err))
            bibitem = BibliographicItem.construct(**bibitem_data)

    return ExternalBibliographicItem(
        source=ExternalSourceMeta(
            id='datatracker',
            home_url="http://datatracker.ietf.org/api",
        ),
        bibitem=bibitem,
        validation_errors=errors,
        requests=[],
    )
