"""Type helpers specific to bibliographic item retrieval."""

import datetime
from pydantic.dataclasses import dataclass
from pydantic import BaseModel
from typing import Mapping, List, Optional
from bib_models.models import BibliographicItem


# Sources
# =======

@dataclass
class SourceMeta:
    """Describes a bibliographic data source."""

    id: str
    """Source ID."""

    home_url: Optional[str] = None
    """Source dataset or external service home page."""

    issues_url: Optional[str] = None
    """Where to file issues."""


@dataclass
class IndexedSourceMeta(SourceMeta):
    """Describes a source that can be indexed in full."""
    pass


@dataclass
class ExternalSourceMeta(SourceMeta):
    """Describes an external source, such as Crossref or Datatracker."""
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
    """Represents a base for sourced bibliographic item,
    including validation errors and sourcing-related details
    specific to the item.

    Generally do not instantiate directly,
    use an appropriate subclass instead.
    """

    bibitem: BibliographicItem

    validation_errors: Optional[List[str]] = None

    details: Optional[str] = None
    """Extra details about this sourcing, human-readable."""


@dataclass
class IndexedObject:
    """Represents an object from an indexed source."""

    name: str
    """Sometimes called “ref”. Filename, etc."""

    external_url: Optional[str]
    """URL, if indexable source makes objects accessible directly."""

    indexed_at: Optional[datetime.date] = None
    """When this object was indexed."""


class IndexedBibliographicItem(SourcedBibliographicItem):
    """A bibliographic item obtained from an indexed source."""

    indexed_object: Optional[IndexedObject]

    source: IndexedSourceMeta


class ExternalBibliographicItem(SourcedBibliographicItem):
    requests: List[ExternalSourceRequest]
    """Requests incurred
    when retrieving info from this source."""

    source: ExternalSourceMeta


class CompositeSourcedBibliographicItem(BibliographicItem):
    """An item obtained by merging bibliographic items
    which were possibly obtained from different sources
    but have one or more identifiers in common."""

    # sourced: List[SourcedBibliographicItem]
    # """Source-specific metadata."""

    sources: Mapping[str, SourcedBibliographicItem]
    """Sourced items.

    Keys should contain source ID and ref (e.g., ref@source-id),
    since there can be multiple refs per source
    and refs can be non-unique across different sources.
    """
