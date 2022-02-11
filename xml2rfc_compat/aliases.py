"""Helpers for working with xml2rfc directory aliases
(symbolic links).

“Actual” directory names are considered those defined in archive source
(see :mod:`xml2rfc_compat.source`). All others are considered aliases.

Aliases are defined via :data:`bibxml.settings.XML2RFC_COMPAT_DIR_ALIASES`
setting.
"""
from typing import List

from django.conf import settings


__all__ = ('ALIASES', 'get_aliases', 'unalias')


ALIASES = getattr(settings, 'XML2RFC_COMPAT_DIR_ALIASES', {})


def get_aliases(dirname: str) -> List[str]:
    """Get aliases for given directory."""

    return ALIASES.get(dirname, [])


def unalias(alias: str) -> str:
    """Resolve provided alias to actual directory."""

    for dirname, aliases in ALIASES.items():
        if alias == dirname or alias in aliases:
            return dirname
    raise ValueError("Not a directory name or alias")
