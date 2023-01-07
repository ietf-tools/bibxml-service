from typing import Union, Tuple, Callable, List

from relaton.models import DocID


__all__ = (
    'DOCID_SERIES_EXTRACTORS',
)


def extract_doi_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'doi':
        return 'DOI', docid.id
    return None


def extract_rfc_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'ietf' and docid.id.lower().startswith('rfc '):
        return 'RFC', docid.id.replace('.', ' ').split(' ')[-1]
    return None


def extract_id_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'internet-draft':
        return 'Internet-Draft', docid.id
    return None


def extract_w3c_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'w3c':
        return 'W3C', docid.id.replace('.', ' ').split('W3C ')[-1]
    return None


def extract_3gpp_tr_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == '3gpp':
        ver = docid.id.split('/')[-1]
        # TODO: This is insufficient
        try:
            id = docid.id.split('3GPP TR ')[1].split(':')[0]
        except IndexError:
            return None
        return '3GPP TR', f'{id} {ver}'
    return None


def extract_ieee_series(docid: DocID) -> Union[Tuple[str, str], None]:
    if docid.type.lower() == 'ieee':
        try:
            id, year, *_ = docid.id.split(' ')[-1].lower().strip().split('.')
        except ValueError:
            return 'IEEE', docid.id
        else:
            return 'IEEE', '%s-%s' % (id.replace('-', '.'), year)
    return None


DOCID_SERIES_EXTRACTORS: List[
    Callable[[DocID], Union[Tuple[str, str], None]]
] = [
    extract_rfc_series,
    extract_id_series,
    extract_w3c_series,
    extract_3gpp_tr_series,
    extract_ieee_series,
    extract_doi_series,
]
"""A list of functions capable of extracting series information
as 2-tuple (series name, document number)
from a :class:`~relaton.models.bibdata.DocID`.
Each function is expected to either return a tuple or ``None``,
and not throw."""
