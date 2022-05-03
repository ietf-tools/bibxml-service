"""Type helpers specific to bibliographic item retrieval."""

from typing import Mapping, List, Optional
import datetime

from pydantic.dataclasses import dataclass
from pydantic import BaseModel

from bib_models import BibliographicItem


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


# Internal sources
# ----------------

@dataclass
class IndexedSourceMeta(SourceMeta):
    """Describes an :term:`indexable source`."""
    pass


@dataclass
class IndexedObject:
    """Represents an object retrieved from an :term:`indexed source`."""

    name: str
    """Sometimes called :term:`ref`. Filename, etc."""

    external_url: Optional[str]
    """URL, if the source makes objects accessible this way."""

    indexed_at: Optional[datetime.date] = None
    """When this object was indexed."""


# External sources
# ----------------

@dataclass
class ExternalSourceMeta(SourceMeta):
    """Describes an external source, such as Crossref or Datatracker."""
    pass


class ExternalSourceRequest(BaseModel):
    """Represents a request to an external source."""

    time: Optional[int] = None
    """How long the request took."""

    url: str
    """Which URL was hit."""


# Sourced bibliographic data
# ==========================

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


class IndexedBibliographicItem(SourcedBibliographicItem):
    """A bibliographic item obtained from an indexed source."""

    indexed_object: Optional[IndexedObject]
    """Indexed object corresponding to this item."""

    source: IndexedSourceMeta
    """Indexed source metadata."""


class ExternalBibliographicItem(SourcedBibliographicItem):
    """Externally sourced bibliographic item."""

    requests: List[ExternalSourceRequest]
    """Requests incurred
    when retrieving info from this source."""

    source: ExternalSourceMeta
    """External source metadata."""


class CompositeSourcedBibliographicItem(BibliographicItem):
    """An item obtained by merging multiple “physical” bibliographic items
    that were possibly obtained from different sources
    but correspond to the same item conceptually.

    Correspondence of multiple “physical” bibliographic items
    is achieved by shared primary document identifier.

    .. seealso::

       - :mod:`bib_models.merger`
       - :func:`main.query_utils.merge_refs`
    """

    sources: Mapping[str, SourcedBibliographicItem]
    """Retrieved documents, keyed by source.

    Keys should contain source ID and ref (e.g., ref@source-id),
    since there can be multiple refs per source
    and refs can be non-unique across different sources.

    Additionally, documents are supposed to be added in order
    “the latest document to the oldest”.
    """

    primary_docid: Optional[str] = None
    """Primary identifier shared by all items.
    If not present, it may indicate source data integrity issue.
    """


class FoundItem(CompositeSourcedBibliographicItem):
    """An item obtained by user searching."""

    headline: str = ''
    """For some types of search, headline highlights search terms
    encountered in context. Expected to be an HTML-formatted string.
    Empty string indicates headline is not available.

    .. seealso::

       - :func:`main.query.search_refs_relaton_field`
         annotates ``RefData`` queryset with ``headline``
         if websearch mode is used.

       - :func:`main.query.build_search_results`
         makes sure ``headline`` annotation makes its way to
         this attribute.
    """
