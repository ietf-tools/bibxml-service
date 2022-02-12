from typing import Optional

from pydantic.dataclasses import dataclass


__all__ = ('Contact', )


@dataclass
class Contact:
    city: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
