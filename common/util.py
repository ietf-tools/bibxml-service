"""List-related utilities."""

from typing import Any, Union, TypeVar, Iterable, List, Optional
import re


T = TypeVar('T')


def flatten(items: Iterable[Any]) -> Iterable[Any]:
    """Flattens an iterable of possibly nested iterables
    (preserving strings, byte arrays and dictionaries)."""

    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes, dict)):
            for sub_x in flatten(x):
                yield sub_x
        else:
            yield x


def as_list(value: Union[T, List[T]]) -> List[T]:
    """Coerces given value to list if needed.

    :param value: any value.
    :returns: the value itself if it’s a list,
              a single-item list with the value
              if the value is neither a list nor ``None``,
              or an empty list if value is ``None``.
    :rtype: list"""

    if isinstance(value, list):
        return value
    elif value is None:
        return []
    else:
        return [value]


def get_fuzzy_match_regex(
    val: str,
    split_sep: str = r'[^a-zA-Z0-9]',
    match_sep: Optional[str] = None,
    deduplicate=False,
) -> str:
    """
    Helper for fuzzy-matching a string using regular expressions.

    Splits a string by given separator regexp,
    and returns a string that can be used to fuzzy-match the string
    by its parts, ignoring the exact separators used.
    (The obtained string can be given in regular expressions.)

    Each string parts inbetween the separators
    are passed through ``re.escape()``.

    :param str val:
        A string like ``foo-bar/foo-bar-1+rr``

    :returns:
        A string like
        ``foo[^a-zA-Z0-9]bar[^a-zA-Z0-9]foo[^a-zA-Z0-9]bar[^a-zA-Z0-9]rr``

    :param str split_sep:
        Used to split the string, by default ``[^a-zA-Z0-9]``

    :param str match_sep:
        Used to concatenate the final regular expression string,
        by default same as ``sep``

    :param bool deduplicate:
        If explicitly set to ``True``,
        repeated parts of the string are omitted.

        .. note:: This may not work with default ``split_sep``/``match_sep``.
    """
    match_sep = match_sep or split_sep
    _parts: List[str] = [
        re.escape(part)
        for part in re.split(split_sep, val)
    ]
    if deduplicate:
        parts = list(dict.fromkeys(_parts))
    else:
        parts = _parts
    return match_sep.join(parts)
