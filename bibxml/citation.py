import datetime
from typing import TypedDict, Literal, Mapping, List, Union, Optional
from pydantic import BaseModel


DocID = Mapping[Union[Literal["id"], Literal["type"]], str]

Link = Mapping[Union[Literal["content"], Literal["type"]], str]

BiblioNote = Mapping[Union[Literal["content"], Literal["type"]], str]

Title = Mapping[
    Union[Literal["content"], Literal["type"], Literal["format"]],
    str]


class Date(TypedDict):
    type: str
    date: datetime.date


class GenericStringValue(TypedDict):
    format: Optional[str]
    script: Optional[str]
    content: str
    language: str


class PersonName(TypedDict):
    completename: Optional[GenericStringValue]


class Contact(TypedDict):
    city: str
    country: str


class Organization(TypedDict):
    name: str
    url: Optional[str]
    contact: Optional[Contact]
    abbreviation: Optional[str]


class PersonAffiliation(TypedDict):
    organization: Organization


class Person(TypedDict):
    name: PersonName
    affiliation: PersonAffiliation


class Contributor(TypedDict):
    role: str
    person: Optional[Person]
    organization: Optional[Organization]


class CopyrightOwner(TypedDict):
    url: str
    name: str
    abbrevation: Optional[str]


Copyright = TypedDict('Copyright', {'from': int, 'owner': CopyrightOwner})


class Citation(BaseModel):
    docid: Union[List[DocID], DocID]
    docnumber: Optional[str] = None
    language: str
    type: str
    doctype: Optional[str] = None
    script: str
    date: Union[List[Date], Date]
    link: Union[List[Link], Link]

    title: Union[List[Title], Title]
    edition: Optional[str] = None
    abstract: Optional[GenericStringValue] = None

    fetched: Optional[datetime.date] = None
    revdate: Optional[datetime.date] = None

    biblionote: Optional[Union[List[BiblioNote], BiblioNote]] = None

    contributor: Union[List[Contributor], Contributor]

    place: Optional[str] = None

    keyword: Optional[Union[List[str], str]] = None

    copyright: Optional[Copyright] = None
