from typing import Any, Set, Tuple, Callable, List, Optional
from urllib.parse import quote_plus
import json

from django.urls import reverse
from django import template

from common.util import as_list as base_as_list


citation_search_base = reverse('search_citations')
get_by_docid_base = reverse('get_citation_by_docid')


register = template.Library()


@register.filter
def as_list(value):
    """Returns the value as a list (see :func:`common.util.as_list`),
    omitting any ``None`` values."""

    result: Any = base_as_list(value)

    return [val for val in result if val is not None and val != '']


@register.filter
def bibitem_link(value: Any):
    """The value can either be a BibliographicItem
    or its dictionary representation.
    This is necessary because source data may not pass
    Pydantic validation.

    If neither is the case, the filter will fall back to search URL
    using given item as query to avoid breaking GUI due to template error.
    """

    id: Optional[str]
    type: Optional[str]

    if hasattr(value, 'docid'):
        try:
            docid = as_list(value.docid or [])[0]
            id, type = docid.id, docid.type
        except (ValueError, IndexError):
            id, type = None, None
    elif isinstance(value, dict):
        try:
            docid = as_list(value.get('docid', []))[0]
            id, type = docid['id'], docid['type']
        except (IndexError, KeyError):
            id, type = None, None

    if id and type:
        return (
            f'{get_by_docid_base}'
            f'?docid={quote_plus(id)}'
            f'&doctype={quote_plus(type)}')

    elif isinstance(value, dict):
        return (
            f'{citation_search_base}'
            f'?query={quote_plus(json.dumps(value))}'
            f'&query_format=json_struct')

    else:
        return (
            f'{citation_search_base}'
            f'?query={quote_plus(str(value))}'
            f'&query_format=websearch')



@register.filter
def substruct_search_link(value: Any, query: str):
    """
    Given structure as value, formats it
    as json_struct bibliographic item search link.

    Query should be in the form 'subfield;param=value;param2=value2'.

    Subfield should be specified as JSON with ``%s`` placeholder
    for the structure given as value, e.g.::

        "contributor": [%s]

    - all keys except comma-separated list in ``only`` param
      will be excluded from value.
    - all comma-separated keys in ``omit`` param will be excluded.
    """

    subfield, *params = query.split(';')

    omitted_keys, only_keys, as_list = _parse_params(params)

    def key_checker(k: str) -> bool:
        return (
            (
                k in only_keys
                or any([
                    ok.startswith(f'{k}.') or ok.startswith(f'{k}[*]')
                    for ok in only_keys
                ])
            ) if only_keys
            else k not in omitted_keys if omitted_keys
            else True
        )

    substruct_json = json.dumps(select_keys(value, key_checker))
    query_json = subfield % substruct_json
    return (
        f'{citation_search_base}'
        f'?query={quote_plus(query_json)}'
        f'&query_format=json_struct')


def _parse_params(params: List[str]) -> Tuple[Set[str], Set[str], bool]:
    omitted_keys: Set[str] = set()
    only_keys: Set[str] = set()
    as_list = False
    for param in params:
        param_name, param_value = param.split('=')
        if param_name == 'omit':
            omitted_keys = omitted_keys | _extract_keys(param_value)
        if param_name == 'only':
            only_keys = only_keys | _extract_keys(param_value)
        if param_name == 'as_list':
            as_list = param_value == 'yes'

    return omitted_keys, only_keys, as_list


def _extract_keys(keys: str) -> Set[str]:
    return set([
        k.strip()
        for k in keys.split(',')
        if k.strip() != ''])


def select_keys(
    value: Any,
    key_checker: Callable[[str], bool],
    prefix='',
) -> Any:
    """
    Selects keys for which value is not None and key itself
    passes the key_checker test.
    """
    if isinstance(value, dict):
        prefix = f'{prefix}.' if prefix else ''
        return {
            key: select_keys(v, key_checker, f'{prefix}{key}')
            for key, v in value.items()
            if key_checker(f'{prefix}{key}') and v is not None
        }
    elif isinstance(value, list):
        prefix = f'{prefix}[*]'
        return [
            select_keys(i, key_checker, prefix)
            for i in value
        ]
    return value
