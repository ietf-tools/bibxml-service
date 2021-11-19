from django import template


register = template.Library()


@register.filter
def as_list(value):
    """Coerces value to list, if needed.

    Returns either the value,
    or a single-item list with value if value is not a list,
    or None if value is None."""

    if isinstance(value, list):
        return value
    elif value is None:
        return None
    else:
        return [value]
