"""Provides an external source registry."""

from typing import Dict, Callable, Any, Optional, Union
import logging
from functools import wraps

from pydantic.dataclasses import dataclass
from pydantic import ValidationError

from bib_models import DocID

from .types import ExternalBibliographicItem
from .exceptions import RefNotFoundError


log = logging.getLogger(__name__)


@dataclass
class ExternalSource:
    """Represents a registered external source."""

    get_item: Union[
        Callable[[str, bool], ExternalBibliographicItem],
        Callable[[str], ExternalBibliographicItem],
    ]
    """Returns an item given docid.id. The ``strict`` argument
    is True by default and means the method must throw
    if received item did not pass validation.
    """

    applies_to: Callable[[DocID], bool]
    """Returns True if this source applies to given identifier.
    Can be used to automatically fetch data from sources.
    """

    primary_for: Callable[[DocID], bool]
    """Returns True if this source is primary to given identifier.
    This means it contains complete authoritative data
    relative to other sources.

    Can be used to automatically fetch data from sources.
    """


def get(id: str) -> ExternalSource:
    """Returns a registered external source by ID."""
    return registry[id]


def register_for_types(id: str, doc_types: Dict[str, bool]):
    def applies_to(docid: DocID) -> bool:
        return doc_types.get(docid.type, None) is not None

    def primary_for(docid: DocID) -> bool:
        return doc_types.get(docid.type, None) == True

    def register_external_source(item_getter: Callable[
        [str, Optional[bool]], ExternalBibliographicItem
    ]):
        registry[id] = ExternalSource(
            applies_to=applies_to,
            primary_for=primary_for,
            get_item=item_getter,
        )
        return item_getter

    return register_external_source


registry: Dict[str, ExternalSource] = {}
"""Registry of external sources."""
