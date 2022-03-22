from typing import Optional, Union, List

from pydantic.dataclasses import dataclass

from .strings import GenericStringValue
from .orgs import Organization


__all__ = ('Person', 'PersonName', 'PersonAffiliation', )


@dataclass
class PersonName:
    """Describes a person’s name."""

    completename: Optional[GenericStringValue] = None
    """Full name."""

    surname: Optional[GenericStringValue] = None
    """Also known as last name or family name."""

    initial: Optional[List[GenericStringValue]] = None
    """Initials, if any."""

    forename: Optional[Union[
        List[GenericStringValue],
        GenericStringValue,
    ]] = None
    """Also known as givne name or first name."""


@dataclass
class PersonAffiliation:
    """Affiliation of a person."""
    organization: Organization


@dataclass
class Person:
    """Describes a person."""

    name: PersonName

    affiliation: Optional[Union[
        List[PersonAffiliation],
        PersonAffiliation,
    ]] = None
