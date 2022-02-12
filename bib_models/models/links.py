from typing import Optional
from pydantic.dataclasses import dataclass


__all__ = ('Link', )


@dataclass
class Link:
    """A typed link."""

    content: str
    """Typically, an URL."""

    type: Optional[str] = None
