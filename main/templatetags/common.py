from typing import Any
import re

from django import template

from common.util import as_list as base_as_list


register = template.Library()


@register.filter
def as_list(value):
    """Returns the value as a list (see :func:`common.util.as_list`),
    omitting any ``None`` values."""

    result: Any = base_as_list(value)

    return [val for val in result if val is not None and val != '']


@register.filter
def split_camel_case(value: str):
    """Converts a camelCased string to its list of components in lowercase.
    Doesn’t do anything if string contains spaces.
    """
    if isinstance(value, str) and ' ' not in value:

        # Separate components by space
        space_separated = re.sub(
            r'''
            (
                (?<=[a-z]) [A-Z]         # lowecase followed by uppercase
                |                        # or
                (?<!\A) [A-Z] (?=[a-z])  # uppercase followed by lowercase
            )
            ''',
            r' \1',
            value,
            flags=re.VERBOSE)

        # Return a list of parts in lowercase
        return [
            part.lower()
            for part in space_separated.split(' ')
        ]
