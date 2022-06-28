from typing import cast, Optional, List, Tuple, Dict, Any
import logging

from pydantic import ValidationError

from common.util import as_list
from common.pydantic import ValidationErrorDict

from relaton.models.bibdata import BibliographicItem


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


def normalize_relaxed(data: Dict[str, Any]):
    """
    Normalizes possibly relaxed/abbreviated deserialized structure,
    where possible, to minimize validation errors.

    Useful with (deserialized) handwritten or poorly normalized JSON/YAML.

    .. important:: Modifies ``data`` in place.

    :rtype dict:
    """
    versions = as_list(data.get('version', []))
    if versions:
        data['version'] = [
            normalize_version(item)
            for item in versions
            if isinstance(item, str)
        ]

    for contributor in data.get('contributor', []):
        person_or_org = contributor.get(
            'person',
            contributor.get(
                'organization',
                {}))
        contacts = as_list(person_or_org.get('contact', []))
        if contacts:
            person_or_org['contact'] = [
                normalize_contact(item)
                for item in contacts
                if isinstance(item, dict)
            ]

    return data


def normalize_version(raw: str) -> Dict[str, Any]:
    """Given a string, returns a dict
    representing a :class:`relaton.bibdata.Versioninfo`.
    """
    if not isinstance(raw, str):
        raise TypeError("normalize_version() takes a string")

    return dict(
        draft=raw,
    )


def normalize_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Given a dict that may represent an address or something else,
    tries to interpret it appropriately
    and return a dict conforming to :class:`relaton.contacts.ContactMethod`.

    May return the same dict as given.
    """
    if not isinstance(raw, dict):
        raise TypeError("normalize_contact() takes a dictionary")

    if (_type := raw.get('type')) and (value := raw.get('value')):
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

    if 'city' in raw or 'country' in raw:
        return dict(
            address=raw,
        )

    return raw
