from typing import cast, Optional, List, Tuple, Dict, Any
import logging

from pydantic import ValidationError

from common.util import as_list
from common.pydantic import ValidationErrorDict

from relaton.models.bibdata import BibliographicItem, DocID


log = logging.getLogger(__name__)


def construct_bibitem(data: Dict[str, Any], strict=True) -> Tuple[
    BibliographicItem,
    Optional[List[ValidationErrorDict]],
]:
    """
    Constructs a :class:`relaton.models.bibdata.BibliographicItem`
    instance, given source data as a dict.

    Optionally, suppresses validation errors and returns them separately
    to be shown to the user.

    May call :func:`.normalize_relaxed` first.

    :param dict data:
        Bibliographic item data as a dict, e.g. deserialized from YAML.

        .. important:: May be modified in-place during normalization.

    :param bool strict:
        See :ref:`strict-validation`.

    :returns:
        a 2-tuple ``(bibliographic item, validation errors)``,
        where errors may be None or a list of Pydantic’s ErrorDicts.

    :raises pydantic.ValidationError:
        Unless ``strict`` is set to ``False``.
    """
    errors: Optional[List[ValidationErrorDict]] = None

    try:
        normalize_relaxed(data)
    except Exception:
        pass

    if strict:
        bibitem = BibliographicItem(**data)
    else:
        try:
            bibitem = BibliographicItem(**data)
        except ValidationError as e:
            log.warn(
                "Unexpected bibliographic item format: %s, %s",
                data.get('docid', 'docid N/A'),
                e)
            errors = cast(List[ValidationErrorDict], e.errors())
            bibitem = BibliographicItem.construct(**data)

    return bibitem, errors


def get_primary_docid(raw_ids: List[DocID]) -> Optional[DocID]:
    """Extracts a single primary document identifier from a list of objects
    as it appears under “docid” in deserialized Relaton data.

    Logs a warning if more than one primary identifier was found.

    :rtype: relaton.models.bibdata.DocID or None
    """

    primary_docids: List[DocID] = [
        docid for docid in raw_ids
        if all([
            docid.primary is True,
            # As a further sanity check, require id and type, but no scope:
            docid.id is not None,
            docid.type is not None,
            docid.scope is None,
        ])
    ]

    deduped = set([frozenset([id.id, id.type]) for id in primary_docids])

    if len(deduped) != 1:
        log.warn(
            "get_primary_docid(): unexpected number of primary docids "
            "found for %s: %s",
            raw_ids,
            len(primary_docids))

    try:
        return primary_docids[0]
    except IndexError:
        return None


def normalize_relaxed(data: Dict[str, Any]):
    """
    Normalizes possibly relaxed/abbreviated deserialized structure,
    where possible, to minimize validation errors.

    Useful with (deserialized) handwritten or poorly normalized JSON/YAML.

    .. important:: Modifies ``data`` in place.

    Is not expected to raise anything.

    :rtype dict:
    """
    versions = as_list(data.get('version', []))
    if versions:
        try:
            data['version'] = [
                (normalize_version(item) if isinstance(item, str) else item)
                for item in versions
            ]
        except Exception:
            pass

    if edition := data.get('edition', None):
        if isinstance(edition, str):
            data['edition'] = {
                'content': edition
            }

    if keywords := data.get('keyword', []):
        data['keyword'] = [
            normalize_maybe_formatted_str(item)
            for item in keywords
        ]

    for contributor in data.get('contributor', []):
        if ((person := contributor.get('person', None))
                or (org := contributor.get('organization', None))):

            # Adapt contacts:
            person_or_org = person or org
            contacts = as_list(person_or_org.get('contact', []))
            if contacts:
                try:
                    person_or_org['contact'] = [
                        normalized
                        for normalized in [
                            normalize_contact(item)
                            for item in contacts
                            if isinstance(item, dict)
                        ]
                        if normalized is not None
                    ]
                except Exception:
                    pass

            if person:
                # Adapt new name format:
                if given_name := person.get('name', {}).get('given', {}):
                    # Forenames that are not initials
                    if actual_forenames := [
                                _name_content
                                for n in given_name.get('forename')
                                if (_name_content := n.get('content', None))
                            ]:
                        person['name']['forename'] = ' '.join(actual_forenames)
                    # Only initials
                    if initials := given_name.get('formatted_initials'):
                        person['name']['initial'] = [initials]
                    # Delete the “given”, not yet supported by relaton-py
                    del person['name']['given']

                # Adapt new affiliated organization format:
                if affiliations := as_list(person.get('affiliation', [])):
                    for affiliation in affiliations:
                        if affiliated_org := affiliation.get('organization', {}):
                            affiliation['organization'] = \
                                normalize_org(affiliated_org)
                    person['affiliation'] = affiliations

            # Adapt new organization name format:
            elif org:
                contributor['organization'] = normalize_org(org)

    return data


def normalize_org(raw: Dict[str, Any]) -> Dict[str, Any]:
    if org_name := raw.get('name', None):
        if isinstance(org_name, list):
            raw['name'] = [normalize_maybe_formatted_str(n) for n in org_name]
        else:
            raw['name'] = [normalize_maybe_formatted_str(org_name)]
    if abbr := raw.get('abbreviation', None):
        raw['abbreviation'] = normalize_maybe_formatted_str(abbr)
    return raw


def normalize_maybe_formatted_str(raw: str | Dict[str, Any]) -> str:
    if isinstance(raw, str):
        return raw
    elif isinstance(raw, dict) and (content := raw.get('content', None)):
        return content
    else:
        return str(raw)


def normalize_version(raw: str) -> Dict[str, Any]:
    """Given a string, returns a dict
    representing a :class:`relaton.models.bibdata.VersionInfo`.
    """
    if not isinstance(raw, str):
        raise TypeError("normalize_version() takes a string")

    return dict(
        draft=raw,
    )


def normalize_contact(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Given a dict that may represent an address or something else,
    tries to interpret it appropriately
    and return a dict conforming
    to :class:`relaton.models.contacts.ContactMethod`.

    May return the same dict as given.
    """
    if not isinstance(raw, dict):
        raise TypeError("normalize_contact() takes a dictionary")

    if (_type := raw.get('type')) and 'value' in raw:
        if value := raw['value']:
            if _type == 'email':
                return dict(
                    email=value,
                )
            if _type in ['uri', 'url']:
                return dict(
                    uri=value,
                )
            if _type == 'phone':
                return dict(
                    phone=dict(
                        content=value,
                    ),
                )
        else:
            # We have a type and a falsey value (probably an empty string)
            return None

    if 'city' in raw or 'country' in raw:
        return dict(
            address=raw,
        )

    if 'phone' in raw and isinstance(raw['phone'], str):
        return dict(
            phone=dict(
                content=raw['phone'],
            ),
        )

    return raw
