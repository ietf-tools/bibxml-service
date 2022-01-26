import logging
from typing import Union

import requests
import requests_cache
from simplejson import JSONDecodeError
from pydantic import ValidationError

from main.exceptions import RefNotFoundError
from sources.doi import get_bibitem
from bib_models.dataclasses import DocID
from .types import ExternalBibliographicItem, CompositeSourcedBibliographicItem


log = logging.getLogger(__name__)


def get_doi_ref(doi: str, strict: bool = True) -> ExternalBibliographicItem:
    """
    :param bool strict: same meaning
                        as in :func:`main.indexed.build_citation_for_docid()`.
    :returns: a :class`bib_models.BibliographicItem` instance
    :rtype BibliographicItem:
    :raises RefNotFoundError: reference not found
    """

    with requests_cache.enabled():
        try:
            sourced_item: Union[ExternalBibliographicItem, None] = \
                get_bibitem(DocID(
                    type='DOI',
                    id=doi,
                ))
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
            params = {
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
