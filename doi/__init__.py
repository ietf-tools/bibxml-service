"""Obtaining bibliographic items by DOI.

Registers an external source.
"""

import logging
from typing import Union, Dict, Any

import requests
import requests_cache
from simplejson import JSONDecodeError
from pydantic import ValidationError

from bib_models import DocID
from main.exceptions import RefNotFoundError
from main.types import ExternalBibliographicItem
from main import external_sources

from .crossref import get_bibitem


log = logging.getLogger(__name__)


@external_sources.register_for_types('doi', {'DOI': False})
def get_doi_ref(
    doi: str,
    strict: bool = True,
) -> ExternalBibliographicItem:
    """
    Obtains an item by DOI.

    :param bool strict: same meaning
                        as in :func:`main.query.build_citation_for_docid()`.
    :rtype: main.types.ExternalBibliographicItem
    :raises main.exceptions.RefNotFoundError: reference not found
    """

    with requests_cache.enabled():
        try:
            sourced_item: ExternalBibliographicItem = \
                get_bibitem(DocID(
                    type='DOI',
                    id=doi,
                ), strict=strict)
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Error connecting to external source")
        except JSONDecodeError:
            raise RuntimeError("Could not decode external source response")
        except RuntimeError:
            raise
        else:
            return sourced_item
