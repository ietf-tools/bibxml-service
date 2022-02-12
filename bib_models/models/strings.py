from typing import Optional, Union, List

from pydantic.dataclasses import dataclass


__all__ = ('FormattedContent', 'GenericStringValue', 'Title', )


@dataclass
class FormattedContent:
    """
    Relaton’s formatted string.
    """
    content: str
    format: Optional[str] = None


@dataclass
class GenericStringValue(FormattedContent):
    """
    Roughly corresponds to a combination
    of Relaton’s localized & formatted string.
    """
    script: Optional[Union[str, List[str]]] = None
    language: Optional[Union[str, List[str]]] = None


@dataclass
class Title(GenericStringValue):
    """
    Typed title.
    """

    type: Optional[str] = None
