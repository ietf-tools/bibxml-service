"""Obtaining bibliographic items by DOI."""

import logging
from typing import Union, Dict, Any

import requests
import requests_cache
from simplejson import JSONDecodeError
from pydantic import ValidationError

from bib_models.dataclasses import DocID
from sources.exceptions import RefNotFoundError
from sources.types import ExternalBibliographicItem
from sources.types import CompositeSourcedBibliographicItem

from .crossref import get_bibitem


log = logging.getLogger(__name__)


def get_doi_ref(
    doi: str,
    strict: bool = True,
) -> CompositeSourcedBibliographicItem:
    """
    Obtains an item by DOI.

    :param bool strict: same meaning
                        as in :func:`main.indexed.build_citation_for_docid()`.
    :rtype: sources.types.CompositeSourcedBibliographicItem
    :raises RefNotFoundError: reference not found
    """

    with requests_cache.enabled():
        try:
            sourced_item: Union[ExternalBibliographicItem, None] = \
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
            if not sourced_item:
                raise RefNotFoundError(
                    "External source returned nothing",
                    doi)
            params: Dict[str, Any] = {
                **sourced_item.bibitem.dict(),
                'sources': {
                    sourced_item.source.id: sourced_item,
                },
            }
            if strict:
                return CompositeSourcedBibliographicItem(**params)
            else:
                try:
                    return CompositeSourcedBibliographicItem(**params)
                except ValidationError:
                    log.exception(
                        "Failed to validate externally fetched "
                        "composite sourced bibliographic item "
                        "%s "
                        "(suppressed with strict=False)",
                        doi)
                    return CompositeSourcedBibliographicItem.construct(
                        **params)
