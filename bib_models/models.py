"""
Some of Relaton models implemented as Pydantic models.
"""

from typing import List, Union, Optional, Any
import datetime

from pydantic import BaseModel, Extra
from pydantic.dataclasses import dataclass

from .dataclasses import DocID, Title
from .dataclasses import Contributor, Copyright, GenericStringValue


@dataclass
class BiblioNote:
    content: str
    type: Optional[str] = None


@dataclass
class Link:
    content: str
    type: Optional[str] = None


@dataclass
class Date:
    type: str
    value: datetime.date


class BibliographicItem(BaseModel, extra=Extra.allow):
    """Relaton’s BibliographicItem expressed as a Pydantic model."""

    docid: Union[List[DocID], DocID]
    docnumber: Optional[str] = None
    language: Optional[Union[List[str], str]] = None
    type: Optional[str] = None
    doctype: Optional[str] = None
    script: Optional[Union[List[str], str]] = None
    date: Optional[Union[List[Date], Date]] = None
    link: Optional[Union[List[Link], Link]] = None

    # TODO: Type BibliographicItem relations properly
    relation: Optional[List[Any]] = None

    title: Optional[Union[List[Title], Title]] = None
    # edition: Optional[str] = None
    abstract: Optional[Union[List[GenericStringValue], GenericStringValue]] = \
        None

    fetched: Optional[Union[datetime.date, str]] = None
    revdate: Optional[Union[datetime.date, str]] = None

    biblionote: Optional[Union[List[BiblioNote], BiblioNote]] = None

    contributor: Optional[List[Contributor]] = None

    place: Optional[Union[List[str], str]] = None

    keyword: Optional[Union[List[str], str]] = None

    copyright: Optional[Union[List[Copyright], Copyright]] = None
