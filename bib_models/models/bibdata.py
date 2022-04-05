"""
Some of Relaton models implemented as Pydantic models.
"""

# NOTE: Docstrings for dataclasses and models below
# may be used when rendering OpenAPI schemas,
# where ReSTructuredText syntax is not
# supported. Stick to plain text.

from __future__ import annotations
from typing import List, Union, Optional
import datetime

from pydantic import BaseModel, Extra, validator
from pydantic.dataclasses import dataclass

from .copyrights import Copyright
from .strings import Title, GenericStringValue
from .people import Person
from .orgs import Organization
from .links import Link
from .dates import Date, validate_relaxed_date


__all__ = (
    'DocID',
    'BibliographicItem',
    'Relation',
    'Contributor',
    'Series',
    'BiblioNote',
)


@dataclass
class DocID:
    """Typed :term:`document identifier`.

    May be given by publisher or issued by some third-party system.
    """

    id: str

    type: str
    """:term:`document identifier type`.
    Determines the format of the ``id`` field.
    """

    primary: Optional[bool] = None
    """If ``True``, this identifier is considered
    a :term:`primary document identifier`.
    """

    scope: Optional[str] = None
    """
    .. todo:: Clarify the meaning of scope.
    """


@dataclass
class BiblioNote:
    """Bibliographic note."""

    content: str
    """Note content."""

    type: Optional[str] = None
    """The class of the note associated with the bibliographic item.
    May be used to differentiate rendering of notes in bibliographies.
    """


class Series(BaseModel):
    """
    A series that given document belongs to.

    Note: formattedref is exclusive with other properties.
    """
    # TODO: Don’t make all properties optional, use union types or something

    formattedref: Optional[Union[GenericStringValue, str]] = None
    """References a bibliographic item via a primary ID.
    Exclusive with other properties.
    """

    title: Optional[Union[
        GenericStringValue,
        List[GenericStringValue]]] = None
    abbrev: Optional[str] = None
    place: Optional[str] = None
    number: Optional[str] = None
    organization: Optional[str] = None
    run: Optional[str] = None
    partnumber: Optional[str] = None
    type: Optional[str] = 'main'


@dataclass
class Contributor:
    """Anyone who helped create or publish the document."""

    role: Union[List[str], str]
    person: Optional[Person] = None
    organization: Optional[Organization] = None


@dataclass
class Edition:
    content: str
    number: Optional[str] = None


class BibliographicItem(BaseModel, extra=Extra.allow):
    """
    Relaton’s main model, bibliographic item.

    Note: formattedref is exclusive with other properties.
    """

    # TODO: Don’t make all optional, use union types or something
    # if Relaton spec makes it clear which properties
    # are mandatory in absence of formattedref.

    formattedref: Optional[Union[GenericStringValue, str]] = None
    """References a bibliographic item via a primary ID.
    Exclusive with other properties.

    Tends to be used, for example, when this bibliographic item
    is used as :data:`.Relation.bibitem`.
    """

    docid: Optional[Union[List[DocID], DocID]] = None

    docnumber: Optional[str] = None
    language: Optional[Union[List[str], str]] = None
    type: Optional[str] = None
    doctype: Optional[str] = None
    script: Optional[Union[List[str], str]] = None
    date: Optional[Union[List[Date], Date]] = None
    link: Optional[Union[List[Link], Link]] = None

    relation: 'Optional[List[Relation]]' = None

    title: Optional[Union[List[Title], Title]] = None
    edition: Optional[Edition] = None
    abstract: Optional[Union[List[GenericStringValue], GenericStringValue]] = \
        None

    fetched: Optional[datetime.date] = None
    revdate: Optional[Union[str, datetime.date, List[Union[str, datetime.date]]]] = None

    biblionote: Optional[Union[List[BiblioNote], BiblioNote]] = None

    contributor: Optional[List[Contributor]] = None

    place: Optional[Union[List[str], str]] = None

    series: Optional[List[Series]] = None

    keyword: Optional[Union[List[str], str]] = None

    copyright: Optional[Union[List[Copyright], Copyright]] = None

    @validator('revdate', pre=True)
    def validate_revdate(cls, v, **kwargs):
        """Validates ``revdate``, allowing it to be unspecific."""
        if isinstance(v, list):
            return [
                validate_relaxed_date(i)
                for i in v
                if i
            ]
        return validate_relaxed_date(v, optional=True)


class Relation(BaseModel, extra=Extra.allow):
    """
    Indicates a relationship from given bibliographic item to another.
    """
    type: str
    """Describes the relationship."""

    bibitem: BibliographicItem
    """Relationship target."""

    description: Optional[GenericStringValue]
    """Describes the relationship in more detail."""


BibliographicItem.update_forward_refs()
