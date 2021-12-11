import requests
from simplejson import JSONDecodeError
import requests_cache
from doi2ietf import process_doi_list

from main.exceptions import RefNotFoundError


def get_doi_ref(ref, format='relaton'):
    """Uses ``doi2ietf`` library to obtain DOI results matching given reference.

    :param format string: "bibxml" or "relaton"
    :returns object: if format is "relaton", the first DOI result as dict.
    :returns string: if format is "bibxml", the first DOI result as XML string.
    :raises RefNotFoundError: reference not found.
    """

    if format not in ['relaton', 'bibxml']:
        raise ValueError("Unknown format requested for DOI ref")

    with requests_cache.enabled():
        doi_format = 'DICT' if format == 'relaton' else 'XML'

        try:
            doi_list = process_doi_list([ref], doi_format)
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Error connecting to external source")
        except JSONDecodeError:
            raise RuntimeError("Could not decode external source response")
        except RuntimeError:
            raise

        if len(doi_list) > 0:
            # TODO: What to do with multiple DOI results for a reference?
            if format == 'relaton':
                return doi_list[0]["a"]
            else:
                return doi_list[0]
        else:
            raise RefNotFoundError(
                "Reference not found: got empty list from DOI",
                ref)
