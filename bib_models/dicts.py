"""
Parts of Relaton BibliographicItem models implemented
as :class:`TypedDict` classes.
"""

from typing import TypedDict, Optional, Union, List


class GenericStringValue(TypedDict):
    content: str
    format: Optional[str]
    script: Optional[Union[str, List[str]]]
    language: Optional[Union[str, List[str]]]


# People
# ======

class Contact(TypedDict):
    city: Optional[str]
    country: Optional[str]


class Organization(TypedDict):
    name: Union[List[str], str]
    contact: Optional[List[Contact]]
    url: Optional[str]
    abbreviation: Optional[str]


class PersonName(TypedDict):
    completename: Optional[GenericStringValue]
    surname: Optional[GenericStringValue]
    forename: Optional[GenericStringValue]


class PersonAffiliation(TypedDict):
    organization: Organization


class Person(TypedDict):
    name: PersonName
    affiliation: Optional[Union[
        List[PersonAffiliation],
        PersonAffiliation,
    ]]


class Contributor(TypedDict):
    role: Union[List[str], str]
    person: Optional[Person]
    organization: Optional[Organization]


# Misc
# ====

class CopyrightOwner(TypedDict):
    name: Union[List[str], str]
    url: Optional[str]
    abbrevation: Optional[str]


Copyright = TypedDict('Copyright', {
    'from': int,
    'owner': Union[List[CopyrightOwner], CopyrightOwner],
})


class DocID(TypedDict):
    type: str
    id: str
    scope: Optional[str]


class Title(TypedDict):
    content: str
    format: Optional[str]
    type: Optional[str]
