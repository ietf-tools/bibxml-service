from typing import Any
from django import template

from common.util import as_list as base_as_list


register = template.Library()


@register.filter
def as_list(value):
    """Returns the value as a list (see :func:`main.util.as_list`),
    or the value itself if it is either ``None``
    or a list containing only ``None`` values."""

    result: Any = base_as_list(value)

    if len(result) == 0 or all([val is None for val in result]):
        return None
    else:
        return result
