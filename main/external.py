import requests
import requests_cache
from simplejson import JSONDecodeError

from sources.doi import get_bibitem
from bib_models.dataclasses import DocID
from .types import SourcedBibliographicItem


def get_doi_ref(doi: str) -> SourcedBibliographicItem:
    """
    :returns: a :class`bib_models.BibliographicItem` instance
    :rtype BibliographicItem:
    :raises RefNotFoundError: reference not found
    """

    with requests_cache.enabled():
        try:
            doi: SourcedBibliographicItem = get_bibitem(DocID(
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
            return doi

        # How do we get:
        # raise RefNotFoundError(
        #     "Reference not found: got empty list from DOI",
        #     ref)
