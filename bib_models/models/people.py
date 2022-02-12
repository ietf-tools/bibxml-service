from typing import Optional, Union, List

from pydantic.dataclasses import dataclass

from .strings import GenericStringValue
from .orgs import Organization


__all__ = ('Person', 'PersonName', 'PersonAffiliation', )


@dataclass
class PersonName:
    completename: Optional[GenericStringValue] = None
    surname: Optional[GenericStringValue] = None
    initial: Optional[List[GenericStringValue]] = None
    forename: Optional[Union[
        List[GenericStringValue],
        GenericStringValue,
    ]] = None


@dataclass
class PersonAffiliation:
    """Affiliation of a person."""
    organization: Organization


@dataclass
class Person:
    name: PersonName
    affiliation: Optional[Union[
        List[PersonAffiliation],
        PersonAffiliation,
    ]] = None
