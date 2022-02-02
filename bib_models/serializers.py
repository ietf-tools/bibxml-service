"""Pluggable serializer registry
for :class:`BibliographicItem` instances.

Currently, only serialization
into various utf-8 strings is supported.
"""

from typing import Callable, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Serializer:
    serialize: Callable[..., str]
    content_type: str


registry: Dict[str, Serializer] = {}


def register(id: str, content_type: str):
    """Parametrized decorator that, given ID and content_type,
    returns a function that will register a serializer function.
    """
    def wrapper(func: Callable[..., str]):
        registry[id] = Serializer(
            serialize=func,
            content_type=content_type,
        )
        return func
    return wrapper


def get(id: str) -> Serializer:
    """Get previously registered serializer by ID."""

    try:
        return registry[id]
    except KeyError:
        raise SerializerNotFound(id)


class SerializerNotFound(RuntimeError):
    """No serializer with given ID."""
    pass
