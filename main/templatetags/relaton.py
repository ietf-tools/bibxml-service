from typing import Any
from django import template

from common.util import as_list as base_as_list


register = template.Library()


@register.filter
def as_list(value):
    """Returns the value as a list (see :func:`common.util.as_list`),
    omitting any ``None`` values."""

    result: Any = base_as_list(value)

    return [val for val in result if val is not None and val != '']
