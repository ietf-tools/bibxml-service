"""
Some of Relaton models implemented as Pydantic models.
"""

from __future__ import annotations
from typing import List, Tuple, Union, Optional
import datetime

from pydantic import BaseModel, Extra, validator
from pydantic.datetime_parse import parse_date
from pydantic.dataclasses import dataclass

from .dataclasses import DocID, Title
from .dataclasses import Contributor, Copyright, GenericStringValue


EXTRA_DATE_FORMATS: List[Tuple[str, str, str]] = [
    ('%Y-%m', '%B %Y', 'month'),
    ('%Y', '%Y', 'year'),
]
"""A list of approximate formats as 3-tuples,
first string of each is ``strptime`` to parse,
second is ``strftime`` to format,
third is specificity ("month" or "year").

Formats should be in order of decreasing specificity.

Used by :func:`relaxed_date_parser()``.
"""


def parse_relaxed_date(v: str) -> Union[None, Tuple[datetime.date, str, str]]:
    """Parses a relaxed date and returns a 3-tuple
    containing date, formatted string, and specificity ("month" or "year").
    """
    for in_f, out_f, specificity in EXTRA_DATE_FORMATS:
        try:
            date = datetime.datetime.strptime(v, in_f).date()
            return date, date.strftime(out_f), specificity
        except ValueError:
            continue

    return None


def validate_relaxed_date(v):
    """To be used as validator on bibliographic item’s pydantic models
    wherever very approximate dates (no day) are possible.

    Tries pydantic’s own validation, which is considered failed
    if returned date is the epoch.

    Then tries ``strptime()`` on each of the :data:`EXTRA_DATE_FORMATS`,
    and returns back a string from ``strftime()``.
    """

    try:
        parsed = parse_date(v)
    except ValueError:
        failed = True
    else:
        failed = parsed == datetime.date(1970, 1, 1)

    if failed:
        parsed_relaxed = parse_relaxed_date(v)
        if parsed_relaxed is not None:
            return parsed_relaxed[1]
        raise ValueError(
            "Failed to parse given string "
            "even as an unspecific date")
    else:
        return parsed


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
    value: Optional[Union[str, datetime.date]]

    @validator('value', pre=True)
    def validate_revdate(cls, v, **kwargs):
        return validate_relaxed_date(v)


class BibliographicItem(BaseModel, extra=Extra.allow):
    """Relaton’s BibliographicItem expressed as a Pydantic model."""

    formattedref: Optional[GenericStringValue] = None
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
    # edition: Optional[str] = None
    abstract: Optional[Union[List[GenericStringValue], GenericStringValue]] = \
        None

    fetched: Optional[datetime.date] = None
    revdate: Optional[Union[str, datetime.date]] = None

    biblionote: Optional[Union[List[BiblioNote], BiblioNote]] = None

    contributor: Optional[List[Contributor]] = None

    place: Optional[Union[List[str], str]] = None

    keyword: Optional[Union[List[str], str]] = None

    copyright: Optional[Union[List[Copyright], Copyright]] = None

    @validator('revdate', pre=True)
    def validate_revdate(cls, v, **kwargs):
        return validate_relaxed_date(v)


class Relation(BaseModel, extra=Extra.allow):
    type: str
    bibitem: BibliographicItem
    description: Optional[GenericStringValue]


BibliographicItem.update_forward_refs()
