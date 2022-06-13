"""Pydantic-related utilities."""

from typing import Any, TypeAlias, List, Tuple, Union, TypedDict, Mapping, cast
from typing import Optional
from dataclasses import asdict, is_dataclass

import datetime
from difflib import SequenceMatcher


__all__ = (
    'ValidationErrorDict',
    'PydanticLoc',
    'get_loc_with_parents',
    'unpack_dataclasses',
    'flatten_and_annotate',
    'AnnotatedField',
)


PydanticLoc: TypeAlias = Tuple[Union[int, str], ...]
"""Normalized Pydantic-style field location,
e.g. ``("date", 0, "type")`` works for ``{date: [{type: 'foo'}]}``.
"""


def get_loc_with_parents(loc: PydanticLoc) -> List[PydanticLoc]:
    """For a :class:`common.pydantic.PydanticLoc` tuple
    (such as ``("date", 0, "type")``)
    returns a list of locs that also include all parent locs
    in order of increasing specificity, e.g.::

        (
            ("date", ),
            ("date", 0),
            ("date", 0, "type"),
        )

    This is used when highlighting schema violations
    in UI generated with the help of :func:`.flatten_and_annotate`.
    """
    result: List[PydanticLoc] = []

    for idx in range(len(loc)):
        result.append(tuple([loc[n] for n in range(idx + 1)]))

    return result


def pretty_print_loc(loc: PydanticLoc) -> str:
    """Given a Pydantic ``loc``, formats it as a string.
    """
    result = ''
    for part in loc:
        if isinstance(part, str):
            result += f'.{part}'
        elif isinstance(part, int):
            if part > 0:
                result += f'#{part + 1}'
    return result.removeprefix('.')


# Some trickery in Pydantic module breaks this:
# from pydantic.error_wrappers import ErrorDict
# ValidationErrorDict: TypeAlias = ErrorDict

class ValidationErrorDict(TypedDict):
    """A Pydantic validation error;
    a list of these is returned by :class:`pydantic.ValidationError`’s
    ``errors()`` method.
    """

    loc: PydanticLoc
    """Normalized representation of field path."""

    msg: str
    """Error description, e.g. ``value is not a valid list``."""

    type: str
    """Error type; e.g., ``type_error.list``."""


def unpack_dataclasses(v: Any):
    """
    Pass it the return value of Pydantic instance’s ``dict()``.

    Recursively walks through the value,
    converting all encountered dataclasses to dictionaries.

    Works around Pydantic’s issues with mixing dataclasses and models.
    """
    if isinstance(v, dict):
        return {
            key: unpack_dataclasses(v)
            for key, v in v.items()
        }
    elif isinstance(v, list):
        return [
            unpack_dataclasses(i)
            for i in v
        ]
    elif is_dataclass(v):
        d = asdict(v)
        return unpack_dataclasses(d)
    else:
        return v


class AnnotatedField(TypedDict):
    """Describes a field with a value
    in a flattened representation provided
    by :func:`~.flatten_and_annotate`.
    """

    pydantic_loc: PydanticLoc
    """A Pydantic-style field locations
    pointing to the field, e.g. ``("date", 0, "type")``.
    """

    validation_errors: List[str]
    """A list of validation error messages
    pertaining to this field."""

    value: Union[int, str, datetime.date, None]
    """Value, can be any simple value (e.g., no mappings or lists)."""


def flatten_and_annotate(
    val,
    validation_errors: Optional[List[ValidationErrorDict]] = None,
    loc: Optional[PydanticLoc] = None,
) -> List[AnnotatedField]:
    """Converts a nested mapping to a list of items,
    where each item associates field path with value and validation errors,
    and corresponding items for “missing field” errors are inserted
    in appropriate places.

    :param dict val:
        Pass the return value of Pydantic instance’s ``dict()`` here.
        As function recurses this value can be any type,
        but it makes an assumption that the initial call will pass a mapping.
    :param list validation_errors:
        If the instance that you pass under ``val`` did not validate,
        pass the output
        of caught ``pydantic.ValidationError``’s ``errors()`` method here.

    :returns: a list of :class:`~.AnnotatedField` instances.

    Other parameters are filled during recursion.
    """
    items: List[AnnotatedField] = []

    validation_errors = validation_errors or []

    if not isinstance(val, Mapping) and loc is None:
        raise ValueError("flatten_hierarchy requires a mapping to start")

    if isinstance(val, Mapping):

        for k, v in val.items():
            next_loc = cast(
                PydanticLoc,
                tuple([*loc, k]) if loc else (k, ))

            items.extend(flatten_and_annotate(
                v,
                validation_errors,
                loc=next_loc,
            ))

        # We want item list to include missing fields
        # as noted by Pydantic’s validation error.

        # In the outer-level call, after all potential recursions…
        if not loc:

            # Gather missing field errors
            not_found_errs = [
                err
                for err in validation_errors
                if err['type'] == 'value_error.missing'
            ]

            # Cycle through missing field errors and insert “dummy” items
            # at appropriate places
            for err in not_found_errs:

                # “dummy” item representing missing field from this error
                err_item: AnnotatedField = {
                    'pydantic_loc': err['loc'],
                    'value': None,
                    'validation_errors': [
                        f"{' → '.join(str(p) for p in err['loc'])}: "
                        f"{err['msg']}"
                    ],
                }

                # Find an item with the key that has the longest match
                # with error’s key, and insert the dummy at that item’s index

                longest_match: Tuple[Optional[int], int] = (None, 0)
                # (item index, shared substring length)

                _err_loc_str = repr(err['loc'])
                for idx, item in enumerate(items):
                    size = SequenceMatcher(
                        None,
                        repr(item['pydantic_loc']),
                        _err_loc_str,
                    ).find_longest_match().size
                    if size > longest_match[1]:
                        longest_match = (idx, size)
                if longest_match[0] is not None:
                    items.insert(longest_match[0], err_item)
                else:
                    # If we failed to find any matches,
                    # possibly a missing top-level is field, just prepend
                    items.insert(0, err_item)

    elif isinstance(val, list):
        enumerated: List[Any] = list(enumerate(val))

        # Cast, since loc is guaranteed not to be None at this point
        # (we accept mappings only at top level):
        _parent_loc = cast(PydanticLoc, loc)

        if len(enumerated) > 1:
            for idx, item in enumerated:
                items.extend(flatten_and_annotate(
                    item,
                    validation_errors,
                    loc=cast(
                        PydanticLoc,
                        tuple([*_parent_loc, idx])),
                ))

        elif len(enumerated) > 0:
            items.extend(flatten_and_annotate(
                val[0],
                validation_errors,
                loc=cast(
                    PydanticLoc,
                    tuple([*_parent_loc, 0])),
            ))

    else:
        loc = cast(PydanticLoc, loc)
        field_errs = [
            f"{' → '.join(str(p) for p in err['loc'])}: "
            f"{err['msg']}"
            for err in validation_errors
            for _loc in get_loc_with_parents(loc)
            if err['loc'] == _loc
        ]
        items.append({
            'validation_errors': field_errs,
            # Cast, since loc is guaranteed not to be None at this point
            # (we only accept mappings at top level):
            'pydantic_loc': loc,
            'value': val,
        })

    return items
