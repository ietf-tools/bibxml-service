"""
Parts of Relaton BibliographicItem models implemented
as simple Python dataclasses.
"""

from typing import TypedDict, Optional, Union, List
from dataclasses import dataclass


@dataclass
class GenericStringValue:
    content: str
    format: Optional[str] = None
    script: Optional[Union[str, List[str]]] = None
    language: Optional[Union[str, List[str]]] = None


# People
# ======

@dataclass
class Contact:
    city: Optional[str] = None
    country: Optional[str] = None


@dataclass
class Organization:
    name: Union[List[str], str]
    contact: Optional[List[Contact]] = None
    url: Optional[str] = None
    abbreviation: Optional[str] = None


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
    organization: Organization


@dataclass
class Person:
    name: PersonName
    affiliation: Optional[Union[
        List[PersonAffiliation],
        PersonAffiliation,
    ]] = None


@dataclass
class Contributor:
    role: Union[List[str], str]
    person: Optional[Person] = None
    organization: Optional[Organization] = None


# Misc
# ====

@dataclass
class CopyrightOwner:
    name: Union[List[str], str]
    url: Optional[str] = None
    abbreviation: Optional[str] = None


# Pydantic dataclasses don’t actually support aliases, contrary to docs
Copyright = TypedDict('Copyright', {
    'from': int,
    'owner': Union[List[CopyrightOwner]],
})


@dataclass
class DocID:
    type: str
    id: str
    scope: Optional[str] = None


@dataclass
class Title(GenericStringValue):
    type: Optional[str] = None
