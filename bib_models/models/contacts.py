from typing import Optional, List

from pydantic.dataclasses import dataclass


__all__ = ('Contact', )


@dataclass
class Contact:
    """Contact information
    for a person or organization."""

    street: List[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
