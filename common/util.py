"""List-related utilities."""


from typing import Any, Union, TypeVar, Iterable, List


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
