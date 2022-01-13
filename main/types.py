"""Type helpers specific to bibliographic item retrieval."""

from pydantic import BaseModel
from typing import TypedDict, Mapping, List, Union, Optional
from bib_models import BibliographicItem, Title, DocID as DocIDModel


class DocID(TypedDict):
    type: str
    id: str
    scope: Optional[str]


class FoundBibliographicItem(BaseModel):
    """Minimum bibliographic item data for search result listing."""

    docid: List[DocID]
    title: List[Title]
    type: Union[List[str], str]
    sources: List[str]


class SourceMeta(BaseModel):
    bibitem: BibliographicItem

    validation_errors: Optional[List[str]] = None

    details: Optional[str] = None
    """Extra source details, human-readable."""

    home_url: Optional[str] = None
    """Source dataset home page."""

    issues_url: Optional[str] = None
    """Where to file issues."""


class InternalSourceMeta(SourceMeta):
    ref: str
    """Ref in source dataset."""


class ExternalSourceRequest(BaseModel):
    """Represents a request to external source."""

    time: Optional[int] = None
    """How long the request took."""

    url: Optional[str] = None
    """Which URL was hit."""


class ExternalSourceMeta(SourceMeta):
    requests: List[ExternalSourceRequest]
    """Requests incurred
    when retrieving info from this source."""


class SourcedBibliographicItem(BibliographicItem):
    sources: Mapping[str, Union[InternalSourceMeta, ExternalSourceMeta]]
    """Source-specific metadata."""
