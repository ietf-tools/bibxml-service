from typing import TypedDict, Optional, Union, List

from pydantic.dataclasses import dataclass


__all__ = ('CopyrightOwner', 'Copyright', )


@dataclass
class CopyrightOwner:
    """Who or which organization holds the copyright.
    """
    name: Union[List[str], str]
    url: Optional[str] = None
    abbreviation: Optional[str] = None


# Pydantic dataclasses don’t actually support aliases, contrary to docs
Copyright = TypedDict('Copyright', {
    'from': int,
    'owner': Union[List[CopyrightOwner]],
})
