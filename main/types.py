"""Type helpers specific to bibliographic item retrieval."""

from pydantic import BaseModel
from typing import Mapping, List, Union, Optional, Dict, Any
from bib_models.models import BibliographicItem
from bib_models.dataclasses import Title, DocID


class FoundBibliographicItem(BaseModel):
    """Minimum bibliographic item data for search result listing."""

    docid: List[DocID]
    title: List[Title]
    type: Union[List[str], str]
    sources: List[str]


class SourceMeta(BaseModel):
    bibitem: Union[BibliographicItem, Dict[str, Any]]

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

    url: str
    """Which URL was hit."""


class ExternalSourceMeta(SourceMeta):
    requests: List[ExternalSourceRequest]
    """Requests incurred
    when retrieving info from this source."""


class SourcedBibliographicItem(BibliographicItem):
    sources: Mapping[str, Union[InternalSourceMeta, ExternalSourceMeta]]
    """Source-specific metadata."""
