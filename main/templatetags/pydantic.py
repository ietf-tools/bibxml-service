from typing import Any, Optional, List

from django import template

from common.pydantic import flatten_and_annotate as base_flatten_annotate
from common.pydantic import PydanticLoc, ValidationErrorDict
from common.pydantic import pretty_print_loc as base_pretty_print_loc


register = template.Library()


@register.filter
def flatten_and_annotate(
    value: dict[str, Any],
    validation_errors: Optional[List[ValidationErrorDict]] = None,
):
    """See :func:`common.pydantic.flatten_and_annotate`."""

    if isinstance(value, dict):
        return base_flatten_annotate(
            value,
            validation_errors)


@register.filter
def pretty_print_loc(loc: PydanticLoc):
    """See :func:`common.pydantic.pretty_print_loc`."""

    return base_pretty_print_loc(loc)


@register.filter
def with_parents(pydantic_loc: PydanticLoc):
    """See :func:`common.pydantic.get_loc_with_parents`."""

    if isinstance(pydantic_loc, tuple):
        result: List[PydanticLoc] = []

        for idx in range(len(pydantic_loc)):
            result.append(tuple([pydantic_loc[n] for n in range(idx + 1)]))

        return result


@register.filter
def get_validation_errors(field_loc, model_errors):
    """Given any number of :class:`PydanticLoc` instances
    in ``field_loc``,
    and a list of Pydantic error dictionaries
    (each containing ``loc``, ``msg``, ``type`` keys),
    returns a ``msg`` string errors matching given
    ``field_loc`` or a ``None`` if no error matches.

    :rtype: str or None
    """
    model_errors = model_errors or []

    # field_loc can be a single PydanticLoc or a list/tuple of them.
    if isinstance(field_loc[0], str):
        locs = (field_loc, )
    else:
        locs = field_loc

    matching_errs = [
        err['msg']
        for err in model_errors
        for loc in locs
        if err['loc'] == loc
    ]

    return ', '.join(matching_errs)
