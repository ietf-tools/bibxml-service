"""Retrieving bibliographic items from indexed Relaton sources."""

import re
import logging
import json
from typing import cast as typeCast, Set, FrozenSet, Optional, Callable
from typing import Dict, List, Union, Tuple, Any

from pydantic import ValidationError

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.contrib.postgres.search import SearchHeadline
from django.db.models.functions import Cast
from django.db.models import TextField
from django.db.models.query import QuerySet, Q
from django.db.models.expressions import RawSQL
from django.db.utils import ProgrammingError, DataError
from django.conf import settings

# from sources import list_internal as list_internal_sources
# from sources import InternalSource

from common.util import as_list
from bib_models.models.bibdata import BibliographicItem, DocID
from bib_models.merger import bibitem_merger

from .exceptions import RefNotFoundError
from .types import IndexedBibliographicItem
from .types import CompositeSourcedBibliographicItem
from .sources import get_source_meta, get_indexed_object_meta
from .models import RefData
from .query_utils import query_suppressing_user_input_error, merge_refs
from .query_utils import get_primary_docid, get_docid_struct_for_search


__all__ = (
    'list_refs',
    'list_doctypes',
    'build_citation_for_docid',
    'build_search_results',
    'search_refs_docids',
    'search_refs_relaton_struct',
    'search_refs_relaton_field',
    'search_refs_json_repr_match',
    'get_indexed_ref',
    'get_indexed_ref_by_quury',
)


log = logging.getLogger(__name__)


def list_refs(dataset_id: str) -> QuerySet[RefData]:
    """Returns all indexed refs in a dataset.

    :param str dataset_id: given Relaton source ID
    :rtype: django.db.models.query.QuerySet[RefData]
    """
    return (
        RefData.objects.filter(dataset__iexact=dataset_id).
        order_by('-latest_date'))


def list_doctypes() -> List[Tuple[str, str]]:
    """Lists all distinct ``docid[*].doctype`` values
    among indexed bibliographic items.

    :returns: a list of 2-tuples of strings
              (document type, example document ID)
    """
    return [
        (i.doctype, i.sample_id)
        for i in (
            RefData.objects.
            # order_by('?').  # This may be inefficient as dataset grows
            raw('''
                select distinct on (doctype) id, doctype, sample_id, latest_date
                from (
                    select id, latest_date, jsonb_array_elements_text(
                        jsonb_path_query_array(
                            body,
                            '$.docid[*].type'
                        )
                    ) as doctype, jsonb_array_elements_text(
                        jsonb_path_query_array(
                            body,
                            '$.docid[*].id'
                        )
                    ) as sample_id
                    from api_ref_data
                ) as item order by doctype, latest_date desc
                ''')
        )
    ]


def search_refs_json_repr_match(text: str, limit=None) -> QuerySet[RefData]:
    """Uses given string to search across serialized JSON representations
    of Relaton citation data.

    .. deprecated:: 2022.2

       It is recommended to use :func:`~.search_refs_relaton_field()`,
       which provides similar behavior.

    Supports PostgreSQL websearch operators like quotes, plus, minus, OR, AND.

    :param str text: the query
    :param int limit: how many results to return at the most
                      (converts to SQL ``LIMIT``)
    :rtype: django.db.models.query.QuerySet[RefData]
    """
    limit = limit or getattr(settings, 'DEFAULT_SEARCH_RESULT_LIMIT', 100)

    return (
        RefData.objects.
        annotate(search=SearchVector(Cast('body', TextField()))).
        filter(search=SearchQuery(text, search_type='websearch')).
        only('ref', 'dataset', 'body').
        order_by('-latest_date')[:limit])


def search_refs_relaton_struct(
        *objs: Union[Dict[Any, Any], List[Any]],
        limit=None) -> QuerySet[RefData]:
    """Uses PostgreSQL’s JSON containment query
    to find bibliographic items containing any of given structures.

    .. note:: Fast, but case-sensitive.

    .. seealso:: PostgreSQL docs on ``@>`` operator.

    :param int limit: how many results to return at the most
                      (converts to SQL ``LIMIT``)
    :returns: ``RefData`` instances where Relaton body contains
              at least one of given ``obj`` structures
    :rtype: django.db.models.query.QuerySet[RefData]
    """
    if len(objs) < 1:
        return RefData.objects.none()

    limit = limit or getattr(settings, 'DEFAULT_SEARCH_RESULT_LIMIT', 100)

    params: List[str] = []
    subqueries = []
    for obj in objs:
        params.append(json.dumps(obj))
        subqueries.append('body @> %s::jsonb')

    query = RawSQL('''
        SELECT id FROM api_ref_data WHERE ({})
    '''.format(' OR '.join(subqueries)), params)

    return (
        RefData.objects.filter(id__in=query).
        only('ref', 'dataset', 'body').
        order_by('-latest_date')[:limit])


def search_refs_relaton_field(
        *field_queries: Dict[str, str],
        exact=False,
        limit=None) -> QuerySet[RefData]:
    """
    Each of ``field_queries`` should be a dictionary of the following shape::

        { '<field spec>': '<query>', '<field spec>': '<query>', ... }

    Returns items for which any of the field queries returns a match.

    .. important:: Do **not** pass user input directly in field specs
                   if you don’t set ``exact`` to ``True``.

    Queries within each dictionary of ``field_queries`` are AND’ed,
    and resulting queries
    (if you pass more than one dict in ``field_queries``)
    are OR’ed.

    :param int limit: Converts to SQL ``LIMIT``.

    :param bool exact: The ``exact`` flag applies to all ``field_queries``
        and determines whether to treat them as JSON path style queries
        or as web search style queries.

        - If ``exact`` is ``False`` (default),
          queries are treated web search style.

          A tsvector from JSON data at each specified field is taken,
          its corresponding query is converted
          to a fuzzy web search tsquery, and `@@` operator is used.

          Wildcards in field path specs are not allowed.

          .. important:: Field path specs are not escaped.
                         Do not pass user input.

          Example::

              { 'docid': 'IEEE', 'keyword': 'foo -bar OR "foo bar"' }

          Empty field spec is treated specially, matching the whole body::

              { '': '"websearch string" anywhere in body' }

        - If ``exact`` is ``True``, queries are treated as JSON path.

          Field specs can be of the shape ``somearray[*].someitem``,
          and their values must be PostgreSQL JSON queries like ``@ == \"%s\"``
          (where ``@`` references current field path).
          The match is done using PostgreSQL’s ``@?`` operator.

          There is more precision than with websearch,
          but it is required to be exact when specifying queries.
          Incorrect syntax will cause a ``ProgrammingError`` or ``DataError``,
          which this function won’t catch.

          Example::

              {
                  'docid[*]': '@.type == "IEEE" && @.id == "some-ieee-id"',
                  'keyword[*]': '@ == "something"',
              }

          Note that the above example will not match a document
          where keyword is not a list,
          only where it is an exact string ``"something"``.

          Empty field spec is treated specially, matching the whole body
          via PostgreSQL’s ``@@`` operator::

              { '': '$.docid[*].id like_regex "(?i)rfc"' }

    :rtype: django.db.models.query.QuerySet[RefData]
    """
    if len(field_queries) < 1:
        return RefData.objects.none()

    limit = limit or getattr(settings, 'DEFAULT_SEARCH_RESULT_LIMIT', 100)

    ored_queries = []
    interpolated_params: List[str] = []

    annotate_headline: Union[None, str] = None

    for idx, fields in enumerate(field_queries):
        anded_queries = []
        for fieldspec, query in fields.items():
            if exact:
                if fieldspec == '':
                    interpolated_params.append(query)
                    anded_queries.append(
                        'body @@ %s',
                    )
                else:
                    interpolated_params.append(
                        '$.{fieldpath} ? ({query})'.format(
                            fieldpath=fieldspec,
                            query=query))
                    anded_queries.append(
                        'body @? %s',
                    )

            else:
                interpolated_params.append(query)
                if fieldspec == '':
                    annotate_headline = 'body'
                    tpl = '''
                        to_tsvector(
                            'english',
                            body
                        ) @@ websearch_to_tsquery('english', %s)
                    '''
                    anded_queries.append(tpl)
                else:
                    tpl = '''
                        to_tsvector(
                            'english',
                            jsonb_build_array({json_selectors})
                        ) @@ websearch_to_tsquery('english', %s)
                    '''
                    anded_queries.append(tpl.format(
                        json_selectors=', '.join([
                            'translate(jsonb_extract_path_text(body, {fieldpath}), \'/\', \' \')'.format(
                                # {fieldpath} is not properly escaped,
                                # callers must not pass user input here.
                                fieldpath=','.join([
                                    "'%s'" % part
                                    for part in fieldpath.split('.')]),
                            ) for fieldpath in fieldspec.split(',')]),
                    ))
        ored_queries.append('(%s)' % ' AND '.join(anded_queries))

    final_query = RawSQL('''
        SELECT id FROM api_ref_data WHERE %s
    ''' % ' OR '.join(ored_queries), interpolated_params)

    # log.debug(
    #     "search_refs_relaton_field: final query",
    #     repr(final_query),
    #     annotate_headline or "no annotation",
    #     field_queries)

    qs = (
        RefData.objects.filter(id__in=final_query).
        order_by('-latest_date'))

    if annotate_headline is not None:
        # This annotation does not seem to cause perceptible impact
        # on performance.
        query = SearchQuery(query, config='english', search_type='websearch')
        qs = qs.annotate(headline=SearchHeadline(
            Cast(annotate_headline, TextField()),
            query,
            start_sel='<mark>',
            stop_sel='</mark>',
            max_words=5,
            min_words=2,
            max_fragments=2,
            config='english',
        ))

    return qs.only('ref', 'dataset', 'body')[:limit]


def search_refs_docids(*ids: Union[DocID, str]) -> QuerySet[RefData]:
    """Given a list of document identifiers
    (``DocID`` instances, or just strings
    which would be treated as ``docid.id``),
    queries and retrieves matching :class:`.models.RefData` objects.

    :rtype: django.db.models.query.QuerySet[RefData]
    """

    # Exact & fast
    struct_queries: List[Any] = [
        struct
        for id in ids
        for struct in (
            {'docid': [get_docid_struct_for_search(id)]}
            if isinstance(id, DocID) else {'docid': [{'id': id}]},
            # Support cases where docid is not a list:
            {'docid': get_docid_struct_for_search(id)}
            if isinstance(id, DocID) else {'docid': {'id': id}},
        )
    ]
    refs = search_refs_relaton_struct(
        *struct_queries,
        limit=15,
    )

    if len(refs) < 1:
        # Less exact, case-insensitive, slower
        jsonpath_queries = [
            {
                'docid[*]':
                '@.id like_regex {id}{type_query}{primary_query}'.format(
                    id=id,
                    type_query=
                        ' && @.type like_regex {id_type}' if id_type else '',
                    primary_query=
                        ' && @.primary == true' if id_primary else '',
                ),
                # To exclude untyped add ' && exists (@.type)'
            }
            for (id, id_type, id_primary) in ((
                '"(?i)^%s$"' % re.escape(
                    id.id
                    if isinstance(id, DocID) else id
                ),
                '"(?i)^%s$"' % re.escape(typeCast(DocID, id).type)
                if getattr(id, 'type', None) else None,
                getattr(id, 'primary', False),
            ) for id in ids)
        ]
        refs = search_refs_relaton_field(
            *jsonpath_queries,
            exact=True,
            limit=15,
        )
        # try:
        #     # Force evaluation
        #     refs[0]
        # except (IndexError, DataError):
        #     # No results or malformed JSON path query
        #     pass

    return refs


def build_citation_for_docid(
    id: str,
    id_type: Optional[str] = None,
    strict: bool = True,
) -> CompositeSourcedBibliographicItem:
    """Retrieves and constructs a ``BibliographicItem``
    for given document identifier (``docid.id`` value).

    Uses indexed sources by querying :class:`.models.RefData`.

    Found bibliographic items (there can be more than one matching given ID)
    are merged into a single composite item
    under a primary document identifier (if any).

    :param str id: :term:`docid.id`
    :param str id_type: Optional :term:`document identifier type`
    :param bool strict: by default is True, and item that fails validation
                        will result in pydantic’s ``ValidationError`` raised.
                        If set to False, item will be constructed anyway,
                        but may contain unexpected data structure—this
                        is intended for cases like forgiving template rendering,
                        and not recommended if returned item is programmatically
                        consumed.

    :rtype: main.types.CompositeSourcedBibliographicItem
    :raises main.exceptions.RefNotFoundError: if no matching refs were found.
    """

    # Retrieve pre-indexed refs
    refs = query_suppressing_user_input_error(
        lambda: search_refs_docids(
            DocID(id, id_type) if id_type else id)
    ) or []

    if len(refs) < 1:
        raise RefNotFoundError("Not found in indexed sources by docid", id)

    # Retrieve bibliographic items with the same primary identifier.
    # This is the preferred scenario.
    primary_docid = get_primary_docid([
        id
        for ref in refs
        for id in as_list(ref.body.get('docid', []))
    ])
    if primary_docid:
        refs = query_suppressing_user_input_error(
            lambda: search_refs_docids(typeCast(DocID, primary_docid))
        ) or []

    return merge_refs(
        refs,
        primary_docid.id if primary_docid else None,
        strict)


DocIDTuple = Tuple[Tuple[str, str], Tuple[str, str]]


def build_search_results(
    refs: QuerySet[RefData],
) -> List[CompositeSourcedBibliographicItem]:
    """Given a :class:`django.db.models.query.QuerySet`
    of :class:`~.models.RefData` entries, build a list
    of :class:`~.types.CompositeSourcedBibliographicItem` objects
    by merging ``RefData`` instances that share
    their primary document identifier.

    :param django.db.models.query.QuerySet[RefData] refs: found refs
    :rtype: List[CompositeSourcedBibliographicItem]
    """

    # Groups refs by primary ID
    # (in absence of such, a ref will go alone under its first ID)
    refs_by_primary_id: Dict[str, List[int]] = {}

    results: List[CompositeSourcedBibliographicItem] = []

    for idx, ref in enumerate(refs):
        suitable_ids: List[Dict[str, Any]] = as_list([
            id
            for id in ref.body.get('docid', [])
            if 'id' in id and 'scope' not in id and 'type' in id
        ])
        if suitable_ids:
            primary_id = get_primary_docid(suitable_ids)
            if primary_id:
                refs_by_primary_id.setdefault(primary_id.id, [])
                refs_by_primary_id[primary_id.id].append(idx)
            else:
                refs_by_primary_id[suitable_ids[0]['id']]

    processed_docids = set[DocIDTuple]()

    for _docid, ref_indexes in refs_by_primary_id.items():
        refs_to_merge: List[RefData] = [refs[idx] for idx in ref_indexes]

        if len(refs_to_merge) > 0:
            results.append(merge_refs(refs_to_merge, _docid, strict=False))

    return results


def get_indexed_ref(dataset_id, ref, format='relaton'):
    """Retrieves a reference from an indexed internal dataset.

    :param str format: "bibxml" or "relaton"
    :returns dict: if format is "relaton", a :class:`dict`.
    :returns str: if format is "bibxml", an XML string.
    :raises RefNotFoundError: either reference or requested format not found
    """

    return get_indexed_ref_by_query(dataset_id, Q(ref__iexact=ref), format)


def get_indexed_ref_by_query(dataset_id, query: Q, format='relaton'):
    """Uses query to retrieve a reference from an indexed internal dataset.

    :param str format: "bibxml" or "relaton"
    :param django.db.models.Q query: query
    :returns: reference in specified format, if available
    :rtype: dict or str, depending on format
    :raises RefNotFoundError: either reference or requested format not found
    """

    if format not in ['relaton', 'bibxml']:
        raise ValueError("Unknown citation format requested")

    try:
        result = RefData.objects.get(
            query &
            Q(dataset__iexact=dataset_id))
    except RefData.DoesNotExist:
        raise RefNotFoundError(
            "Cannot find matching reference in given dataset",
            repr(Q))
    except RefData.MultipleObjectsReturned():
        raise RefNotFoundError(
            "Multiple references match query in given dataset",
            repr(Q))

    if format == 'relaton':
        return result.body

    else:
        bibxml_repr = result.representations.get('bibxml', None)
        if bibxml_repr:
            return bibxml_repr
        else:
            raise RefNotFoundError(
                "BibXML representation not found for requested reference",
                repr(Q))
