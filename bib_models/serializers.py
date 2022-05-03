"""Pluggable serializer registry
for :class:`~.models.bibdata.BibliographicItem` instances.

Currently, only serialization
into various utf-8 strings is supported.
"""

from typing import Callable, Dict
from dataclasses import dataclass


def register(id: str, content_type: str):
    """Parametrized decorator that, given ID and content_type,
    returns a function that will register a serializer function.

    Serializer function must take
    a :class:`relaton.models.bibdata.BibliographicItem` instance
    and return an utf-8-encoded string.
    """
    def wrapper(func: Callable[..., bytes]):
        registry[id] = Serializer(
            serialize=func,
            content_type=content_type,
        )
        return func
    return wrapper


@dataclass
class Serializer:
    """A registered serializer.
    Instantiated automatically by the :func:`~bib_models.serializers.register`
    function.
    """
    serialize: Callable[..., bytes]
    """Serializer function. Returns a string."""

    content_type: str
    """Content type to be used with this serializer, e.g. in HTTP responses."""


def get(id: str) -> Serializer:
    """Get previously registered serializer by ID.

    :raises SerializerNotFound:"""

    try:
        return registry[id]
    except KeyError:
        raise SerializerNotFound(id)


class SerializerNotFound(RuntimeError):
    """No registered serializer with given ID."""
    pass


registry: Dict[str, Serializer] = {}
"""Registry of serializers."""
