"""Retrieving Internet Drafts from Datatracker.

Registers :func:`.get_internet_draft()`
as an :term:`external source` of bibliographic data
for “Internet-Draft” document identifier type.
"""

import logging
from typing import Dict, Any, List, Tuple
import ast
import datetime
import re
import json

import requests

from bib_models import construct_bibitem
from main.types import ExternalBibliographicItem, ExternalSourceMeta
from main.exceptions import RefNotFoundError
from main import external_sources

from .request import get, BASE_DOMAIN


__all__ = (
    'get_internet_draft',
    'remove_version',
    'version_re',
)


log = logging.getLogger(__name__)


version_re = re.compile(r'^(?P<versionless>[-\w]+?)(\-(?P<version>\d{2}))?$')
"""A regular expression that allows extracting
a version or a versionless name from an Internet Draft name
that possibly has version."""


def remove_version(id: str) -> Tuple[str, str]:
    """
    Extracts a version from a possibly versioned Internet Draft ID,
    and returns a 2-tuple of strings: versionless ID
    and optionally version (or None).
    """

    match = version_re.match(id)

    if not match or not match.group('versionless'):
        raise ValueError("Invalid Datatracker ID: %s" % id)

    versionless = match.group('versionless')

    return versionless, match.group('version')


@external_sources.register_for_types('datatracker', {'Internet-Draft': True})
def get_internet_draft(
    docid: str,
    strict: bool = True,
) -> ExternalBibliographicItem:
    """Retrieves an Internet Draft from Datatracker in Relaton format.

    Makes necessary requests to Datatracker API
    and converts .

    :param str docid:
    :param bool strict: see :ref:`strict-validation`
    :rtype: main.types.ExternalBibliographicItem
    """

    # We cannot request a particular I-D version from Datatracker,
    # so we ignore the second tuple element (version)
    versionless, _ = remove_version(docid)

    resp = get(f'/api/v1/doc/document/{versionless}/')

    if resp.status_code == 404:
        raise RefNotFoundError()

    data = resp.json()
    data['resource_uri'] = data.get('resource_uri').replace('api/v1/doc/document/', 'doc/html/')

    bibitem_data: Dict[str, Any] = dict(
        type='draft',
        abstract=[{
            'content': data['abstract'],  # .replace('\n', ' '),
        }] if 'abstract' in data else None,
        link=[{
            'content': f'{BASE_DOMAIN}%s' % data['resource_uri'],
        }],
        version=[{
            'draft': data['rev'],
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
        contributor=[],
    )

    # Some data (e.g., authors and dates) is only available
    # via separate submission endpoint
    try:
        latest_submission_url = data['submissions'][-1]
    except IndexError:
        log.warning(
            "Unable to retrieve complete Internet Draft metadata: "
            "no submissions available")
    else:
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
                            # IMPORTANT: Using literal_eval means we assume
                            # Datatracker’s responses are always trustworthy.
                            # The reason we’re using it is because Datatracker
                            # appears to return something like Python’s repr()
                            # of a list sometimes here
                            # (i.e., not JSON-decodable)
                            authors = ast.literal_eval(
                                latest_submission_data['authors'])
                        except (ValueError, SyntaxError):
                            authors = []
                else:
                    authors = []
                if authors:
                    bibitem_data['contributor'] += [
                        {
                            'role': ['author'],
                            'person': {
                                'name': {
                                    'completename': {
                                        'content': a['name']
                                    },
                                },
                            },
                        }
                        for a in authors
                    ]

    bibitem, errors = construct_bibitem(bibitem_data, strict)

    return ExternalBibliographicItem(
        source=ExternalSourceMeta(
            id='datatracker',
            home_url="http://datatracker.ietf.org/api",
        ),
        bibitem=bibitem,
        validation_errors=errors,
        requests=[],  # TODO: Provide requests incurred later
    )
