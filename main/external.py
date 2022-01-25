from typing import Union
import requests
import requests_cache
from simplejson import JSONDecodeError

from main.exceptions import RefNotFoundError
from sources.doi import get_bibitem
from bib_models.dataclasses import DocID
from .types import ExternalBibliographicItem, CompositeSourcedBibliographicItem


def get_doi_ref(doi: str) -> ExternalBibliographicItem:
    """
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
            return CompositeSourcedBibliographicItem.construct(
                **sourced_item.bibitem.dict(),
                sources={
                    sourced_item.source.id: sourced_item,
                },
            )
