"""
Some of Relaton models implemented as Pydantic models.
"""

from typing import List, Tuple, Union, Optional, Any
import datetime

from pydantic import BaseModel, Extra, validator
from pydantic.datetime_parse import parse_date
from pydantic.dataclasses import dataclass

from .dataclasses import DocID, Title
from .dataclasses import Contributor, Copyright, GenericStringValue


EXTRA_DATE_FORMATS: List[Tuple[str, str]] = [
    ('%Y-%m', '%B %Y'),
    ('%Y', '%Y'),
]
"""A list of approximate formats as 2-tuples,
first string of each is ``strptime`` to parse,
second is ``strftime`` to format.

Formats should be in order of decreasing specificity.

Used by :func:`relaxed_date_parser()``.
"""


def relaxed_date_parser(v):
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
        for in_f, out_f in EXTRA_DATE_FORMATS:
            try:
                return (
                    datetime.datetime.
                    strptime(v, in_f).
                    date().strftime(out_f)
                )
            except ValueError:
                continue
        raise ValueError("Failed to parse given string as a date")
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
        return relaxed_date_parser(v)


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

    # TODO: Type BibliographicItem relations properly
    relation: Optional[List[Any]] = None

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
        return relaxed_date_parser(v)
