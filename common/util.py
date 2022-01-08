from typing import Union, TypeVar, List


T = TypeVar('T')


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
