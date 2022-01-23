"""Type helpers specific to bibliographic item retrieval."""

import datetime
from pydantic.dataclasses import dataclass
from pydantic import BaseModel
from typing import Mapping, List, Union, Optional, Dict, Any
from bib_models.models import BibliographicItem


# Sources
# =======

@dataclass
class SourceMeta:
    id: str
    """Source ID."""

    home_url: Optional[str] = None
    """Source dataset or external service home page."""

    issues_url: Optional[str] = None
    """Where to file issues."""


@dataclass
class IndexedSourceMeta(SourceMeta):
    indexed_at: Optional[datetime.date] = None


@dataclass
class ExternalSourceMeta(SourceMeta):
    pass


class ExternalSourceRequest(BaseModel):
    """Represents a request to external source."""

    time: Optional[int] = None
    """How long the request took."""

    url: str
    """Which URL was hit."""


# Sourced items
# =============

class SourcedBibliographicItem(BaseModel):
    bibitem: Union[BibliographicItem, Dict[str, Any]]

    validation_errors: Optional[List[str]] = None

    details: Optional[str] = None
    """Extra details about this sourcing, human-readable."""


class IndexedBibliographicItem(SourcedBibliographicItem):
    ref: str
    """Ref in source dataset."""

    source: IndexedSourceMeta


class ExternalBibliographicItem(SourcedBibliographicItem):
    requests: List[ExternalSourceRequest]
    """Requests incurred
    when retrieving info from this source."""

    source: ExternalSourceMeta


class CompositeSourcedBibliographicItem(BibliographicItem):
    """An item obtained by merging sourced items with the same ID."""

    # sourced: List[SourcedBibliographicItem]
    # """Source-specific metadata."""

    sources: Mapping[str, SourcedBibliographicItem]
    """Source-specific metadata.
    Keys contain source ID and ref (e.g., ref@source-id),
    since there can be multiple refs per source
    and refs can be non-unique across different sources.
    """
