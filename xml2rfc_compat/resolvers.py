"""Implements a basic registry
of xml2rfc-style path resolver (fetcher) functions
and anchor formatter functions.
"""

from typing import Callable, Dict, Optional, TypeAlias

from bib_models import BibliographicItem


FetcherFunc: TypeAlias = Callable[[str], BibliographicItem]

fetcher_registry: Dict[str, FetcherFunc] = {}
"""Maps xml2rfc subdirectory name to a function
that returns a bibliographic item given xml2rfc path substring."""


AnchorFormatterFunc: TypeAlias = \
    Callable[[str, Optional[BibliographicItem]], str]

anchor_formatter_registry: Dict[str, AnchorFormatterFunc] = {}
"""Maps xml2rfc subdirectory name to a function
that returns an anchor, given xml2rfc path substring
and possibly resolved bibliographic item."""


def register_fetcher(dirname: str):
    """Parametrized decorator that returns a registering function
    for :term:`xml2rfc fetcher function` to be associated with given top-level
    xml2rfc directory name.
    """
    def _register_fetcher(func: FetcherFunc):
        fetcher_registry[dirname] = func
        return func
    return _register_fetcher


def register_anchor_formatter(dirname: str):
    """Parametrized decorator that returns a registering function
    for an :term:`anchor formatter function` to be associated with given
    xml2rfc directory name.
    """
    def _register_anchor_formatter(func: AnchorFormatterFunc):
        anchor_formatter_registry[dirname] = func
        return func
    return _register_anchor_formatter
