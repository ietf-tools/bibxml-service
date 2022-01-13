"""
Some of Relaton models implemented as Pydantic models.

Makes use of ``TypedDict``-based definitions from :mod:`dict`
to reduce duplication.

.. note::

   TypedDict definitions don’t allow default values.

   This means model fields using TypedDict will require
   passing ``None`` for fields that are ``Optional[]``
   in TypedDict specifications.

   Resist the temptation to go ``total=False`` on TypedDicts,
   since that would disable warnings for missing field validation.
"""

from typing import List, Union, Optional
import datetime

from pydantic import BaseModel

from .dicts import DocID, Title
from .dicts import Contributor, Copyright, GenericStringValue


class BiblioNote(BaseModel):
    content: str
    type: Optional[str] = None


class Link(BaseModel):
    content: str
    type: Optional[str] = None


class Date(BaseModel):
    type: str
    value: datetime.date


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
    # edition: Optional[str] = None
    abstract: Optional[Union[List[GenericStringValue], GenericStringValue]] = \
        None

    fetched: Optional[Union[datetime.date, str]] = None
    revdate: Optional[Union[datetime.date, str]] = None

    biblionote: Optional[Union[List[BiblioNote], BiblioNote]] = None

    contributor: Optional[Union[List[Contributor], Contributor]] = None

    place: Optional[Union[List[str], str]] = None

    keyword: Optional[Union[List[str], str]] = None

    copyright: Optional[Union[List[Copyright], Copyright]] = None
