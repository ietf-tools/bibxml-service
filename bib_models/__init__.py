"""Pydantic versions for some of Relaton models."""

from typing import TypedDict, List, Union, Optional
import datetime

from pydantic import BaseModel


class DocID(BaseModel):
    type: str
    id: str
    scope: Optional[str] = None


class Title(BaseModel):
    content: str
    format: Optional[str] = None
    type: Optional[str] = None


class BiblioNote(BaseModel):
    content: str
    type: Optional[str] = None


class Link(BaseModel):
    content: str
    type: Optional[str] = None


class Date(BaseModel):
    type: str
    value: datetime.date


class GenericStringValue(BaseModel):
    content: str
    format: Optional[str] = None
    script: Optional[Union[str, List[str]]] = None
    language: Optional[Union[str, List[str]]] = None


class PersonName(BaseModel):
    completename: Optional[GenericStringValue] = None


class Contact(BaseModel):
    city: Optional[str] = None
    country: Optional[str] = None


class Organization(BaseModel):
    name: str
    url: Optional[str] = None
    contact: Optional[Contact] = None
    abbreviation: Optional[str] = None


class PersonAffiliation(BaseModel):
    organization: Organization


class Person(BaseModel):
    name: PersonName
    affiliation: Optional[PersonAffiliation] = None


class Contributor(BaseModel):
    role: Union[List[str], str]
    person: Optional[Person] = None
    organization: Optional[Organization] = None


class CopyrightOwner(BaseModel):
    name: Union[List[str], str]
    url: Optional[str] = None
    abbrevation: Optional[str] = None


# ``from`` is reserved, so we use TypedDict instead of a Pydantic model.
# TODO: Define Copyright as a Pydantic model
# (figure out how to use reserved identifiers as fields)
Copyright = TypedDict('Copyright', {
    'from': int,
    'owner': Union[List[CopyrightOwner], CopyrightOwner],
})


class BibliographicItem(BaseModel):
    """Relaton’s ``BibliographicItem`` expressed as a Pydantic model."""

    docid: Union[List[DocID], DocID]
    docnumber: Optional[str] = None
    language: Optional[Union[List[str], str]] = None
    type: Optional[str] = None
    doctype: Optional[str] = None
    script: Optional[Union[List[str], str]] = None
    date: Optional[Union[List[Date], Date]] = None
    link: Optional[Union[List[Link], Link]] = None

    title: Optional[Union[List[Title], Title]] = None
    edition: Optional[str] = None
    abstract: Optional[Union[List[GenericStringValue], GenericStringValue]] = \
        None

    fetched: Optional[Union[datetime.date, str]] = None
    revdate: Optional[Union[datetime.date, str]] = None

    biblionote: Optional[Union[List[BiblioNote], BiblioNote]] = None

    contributor: Optional[Union[List[Contributor], Contributor]] = None

    place: Optional[Union[List[str], str]] = None

    keyword: Optional[Union[List[str], str]] = None

    copyright: Optional[Union[List[Copyright], Copyright]] = None
