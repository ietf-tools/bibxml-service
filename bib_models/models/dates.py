from typing import List, Tuple, Union, Optional
import datetime

from pydantic import validator
from pydantic.dataclasses import dataclass
from pydantic.datetime_parse import parse_date


__all__ = (
  'Date',
  'parse_relaxed_date',
  'parse_date_pydantic',
  'validate_relaxed_date',
  'EXTRA_DATE_FORMATS',
)


@dataclass
class Date:
    """A typed date."""

    value: Optional[Union[str, datetime.date]]
    """Date value.

    Can either be a fully-formed date,
    or a low-specificity date like YYYY or YYYY-MM.
    """

    type: str

    @validator('value', pre=True)
    def validate_value(cls, v, **kwargs):
        """Validates ``value``, allowing it to be unspecific."""
        return validate_relaxed_date(v)


EXTRA_DATE_FORMATS: List[Tuple[str, str, str]] = [
    ('%Y-%m', '%B %Y', 'month'),
    ('%B %Y', '%B %Y', 'month'),
    ('%Y', '%Y', 'year'),
]
"""A list of approximate formats as 3-tuples,
first string of each is :func:`datetime.datetime.strptime` to parse,
second is :func:`datetime.datetime.strftime` to format,
third is specificity ("month" or "year").

Formats should be in order of decreasing specificity.

Used by :func:`.parse_relaxed_date()`.
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


def parse_date_pydantic(v) -> Union[datetime.date, None]:
    """Parses given date or string using Pydantic’s ``parse_date()``,
    which must return a date or raise a subclass of :class:`ValueError`.

    It’s considered failed if the obtained date is the epoch
    (which is one of Pydantic parser’s failure modes).
    """
    try:
        parsed = parse_date(v)
    except ValueError:
        return None
    else:
        return parsed if parsed != datetime.date(1970, 1, 1) else None


def validate_relaxed_date(v, optional=False):
    """To be used as validator on bibliographic item’s pydantic models
    wherever very approximate dates (no day) are possible.

    Tries pydantic’s own validation, which is considered failed
    if returned date is the epoch.

    Then tries ``strptime()`` on each of the :data:`EXTRA_DATE_FORMATS`,
    and returns back a string from ``strftime()``.
    """

    if optional and v is None:
        return None

    parsed = parse_date_pydantic(v)

    if not parsed:
        parsed_relaxed = parse_relaxed_date(v)

        if parsed_relaxed is not None:
            return parsed_relaxed[1]

        raise ValueError(
            "Failed to parse given string "
            "even as an unspecific date")
    else:
        return parsed
