"""Pydantic-related utilities."""

from typing import Any
from dataclasses import asdict, is_dataclass


def unpack_dataclasses(v: Any):
    """
    Recursively walks through the value,
    converting all encountered dataclasses to dictionaries.

    Works around Pydantic’s inability to mix dataclasses and models.
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
