"""Retrieving bibliographic items from indexed Relaton sources."""

import re
import logging
import json
from typing import cast as typeCast, Optional
from typing import Dict, List, Union, Tuple, Any

from django.contrib.postgres.search import SearchQuery
from django.contrib.postgres.search import SearchHeadline
from django.db.models.functions import Cast
from django.db.models import TextField
from django.db.models.query import QuerySet, Q
from django.db.models.expressions import RawSQL
from django.conf import settings

# from sources import list_internal as list_internal_sources
# from sources import InternalSource

from common.util import as_list
from bib_models import DocID, Relation
from bib_modles.util import construct_bibitem, get_primary_docid

from .exceptions import RefNotFoundError
from .types import IndexedBibliographicItem
from .types import CompositeSourcedBibliographicItem, FoundItem
from .sources import get_source_meta, get_indexed_object_meta
from .models import RefData
from .query_utils import query_suppressing_user_input_error, compose_bibitem
from .query_utils import get_docid_struct_for_search


__all__ = (
    'list_refs',
    'list_doctypes',
    'build_citation_for_docid',
    'build_search_results',
    'hydrate_relations',
    'search_refs_docids',
    'search_refs_relaton_struct',
    'search_refs_relaton_field',
    'search_refs_json_repr_match',
    'get_indexed_item',
    'get_indexed_ref_by_query',
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

    # More flexible in theory and could be annotated with headline,
    # but may not yield exact string matches for some reason.
    # return (
    #     RefData.objects.
    #     annotate(search=SearchVector(Cast('body', TextField()))).
    #     filter(search=SearchQuery(text, search_type='websearch')).
    #     only('ref', 'dataset', 'body').
    #     order_by('-latest_date')[:limit])

    return (
        RefData.objects.
        filter(body__icontains=text).
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
                    type_query=(
                        ' && @.type like_regex {id_type}' if id_type else ''),
                    primary_query=(
                        ' && @.primary == true' if id_primary else ''),
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
    hydrate_relation_levels: int = 1,
    resolved_item_cache:
    Optional[Dict[str, Optional[CompositeSourcedBibliographicItem]]] = None,
) -> CompositeSourcedBibliographicItem:
    """Retrieves and constructs a ``BibliographicItem``
    for given document identifier (``docid.id`` value).

    Uses indexed sources by querying :class:`.models.RefData`.
    Found bibliographic items (there can be more than one matching given ID)
    are merged into a single composite item
    under a primary document identifier (if any).

    It is different from :func:`~.get_indexed_item` in that *this* function
    uses ``docid.id``, instead of dataset-specific reference (such as filename).
    This also means that there can be multiple bibliographic items
    matching given document ID among different datasets,
    which is why a composite bibliographic item is returned.
    This function is also more expensive and incurs multiple DB queries.

    :param str id: :term:`docid.id`
    :param str id_type: Optional :term:`document identifier type`
    :param bool strict: see :ref:`strict-validation`
    :param int hydrate_relation_levels:
        see ``depth`` in :func:`~.hydrate_relations()`
    :param dict resolved_item_cache:
        see :func:`~.hydrate_relations()`

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

    # Retrieve additional bibliographic items
    # with the same primary identifier, if one is available.
    primary_docid = get_primary_docid([
        DocID(**id)
        for ref in refs
        for id in as_list(ref.body.get('docid', []))
    ])
    if primary_docid:
        refs = query_suppressing_user_input_error(
            lambda: search_refs_docids(typeCast(DocID, primary_docid))
        ) or []

    composite_item, valid = compose_bibitem(
        refs,
        primary_docid.id if primary_docid else None,
        strict)

    # Do the same for relations, if requested
    if valid and hydrate_relation_levels > 0 and composite_item.relation:
        hydrate_relations(
            composite_item.relation,
            strict=strict,
            depth=hydrate_relation_levels,
            resolved_item_cache=resolved_item_cache or {},
        )

    return composite_item


def hydrate_relations(
    relations: List[Relation],
    strict: bool = True,
    depth: int = 1,
    resolved_item_cache:
        Optional[Dict[str, Optional[CompositeSourcedBibliographicItem]]] = None
):
    """
    For every :class:`~relaton.models.bibdata.Relation`
    of given list of ``relations``, calls :func:`~.build_citation_for_docid()`
    on related bibliographic item,
    and replaces relation’s ``bibitem`` with the result.

    This lets sources avoid specifying full bibliographic data
    on every relation, reducing duplication.
    If full bibliographic data for related item
    can be assumed to be provided by another authoritative source,
    a ``docid`` with :term:`primary document identifier` is enough.

    .. important::

       The function alters an attribute on each list item
       **in place** and returns nothing.

       As a result, each relation’s ``bibitem`` can be expected to conform
       to :class:`~main.types.CompositeSourcedBibliographicItem`,
       rather than :class:`~relaton.models.bibdata.BibliographicItem`.

       It should also have more complete data under its ``bibitem``
       attribute, ideally.

    :param list relations:
        A list of :class:`~relaton.models.bibdata.Relation` instances,
        possibly shallow (containing no data except primary identifier).

    :param bool strict: see :ref:`strict-validation`

    :param int depth:
        How many relation levels to recurse
        (through :func:`~.build_citation_for_docid()`) into.

        If larger than zero, this function calls itself
        to query available sources for each relation’s bibitem
        and replaces it with CompositeSourcedBibliographicItem.
        This value is decremented on each recursion level.
        When zero, relations are left alone and recursion stops.

    :param dict resolved_item_cache:
        A cache containing document identifiers mapped to already-resolved
        bibliographic item data.
        If a given docid is found in the dictionary, no DB queries are made
        for that relation.

        .. note::

           This structure is updated in place during function runtime.
    """
    cache: Dict[str, Optional[CompositeSourcedBibliographicItem]] = \
        resolved_item_cache or {}

    for relation in relations:
        if _docid := get_primary_docid(relation.bibitem.docid):
            _id = _docid.id
            _type = _docid.type

            id_key = f'{_type}:{_id}'

            # Fill in cache for this item.
            if id_key not in cache:
                try:
                    cache[id_key] = build_citation_for_docid(
                        _id,
                        _type,
                        strict,
                        depth - 1,
                        # ^ it’s important to decrement this,
                        # or we may recurse infinitely
                        # since circular relations are very much
                        # a possibility.
                        cache,
                    )
                except Exception as err:
                    # XXX: Catch more specific exceptions?
                    # We have failed to obtain a hydrated item
                    # for this relation, store None in cache.
                    log.warn(
                        "Failed to hydrate related bibitem %s, %s: %s",
                        _type,
                        _id,
                        err)
                    cache[id_key] = None

            # Switch original bibitem on this relation
            # to hydrated item in cache, if any. Hydrated item,
            # which is CompositeSourcedBibliographicItem,
            # inherits from Relaton’s BibliographicItem
            # and thus is safe to use in its place.
            #
            # TODO: Express this using Python type system somehow,
            # if possible without excess duplication and workarounds.
            #
            # NOTE: mypy doesn’t seem to type check this assignment.
            if id_key in cache and cache[id_key]:
                relation.bibitem = typeCast(
                    CompositeSourcedBibliographicItem,
                    cache[id_key],
                )


def refdata_to_bibitem(
    ref_data: Dict[str, Any],
    resolved_items:
        Optional[Dict[str, CompositeSourcedBibliographicItem]] = None,
    hydrate_relation_levels: int = 1,
) -> CompositeSourcedBibliographicItem:
    """
    Given a representation of bibliographic item as found on ``RefData.body``
    (aka Relaton bibitem YAML deserialized into a generic dictionary),
    attempts to complete its data by querying available sources.

    :returns:
        The same logical bibliographic item, but represented by
        :class:`main.types.CompositeSourcedBibliographicItem`
        and ideally with more complete data.

    In some cases, an item in the source may contain
    as little as just a ``docid`` property.
    Typically this happens when the item is present as a relation
    on another item.

    The logic for completing such item’s data is:

    1. Find bibliographic item’s :term:`primary document identifier`

    2. Query available bibliographic data sources for any items
       that have the same primary docid,
       and merge results
       into a :class:`main.types.CompositeSourcedBibliographicItem`
       (see :func:`main.query_utils.compose_bibitem()`)

    4. If ``hydrate_relation_levels`` is larger than zero,
       do the above for each relation
       (call this function recursively
       with ``hydrate_relation_levels`` decremented by one),
       replace relation’s ``bibitem`` with the result

    5. Return the composite item created on step 3.

    :param dict resolved_items:
        A cache containing primary docid mapped to already-resolved
        bibliographic item data.

        - If an item is found in this cache, no DB query is made.
        - The cache is updated as a side-effect of this function run.

        If item is found in the dictionary, no DB queries are made
        and the dictionary is used for resolving relations.

    :param int hydrate_relation_levels:
        How many relation levels to recurse into.
        Decremented on each recursion.
        If zero, relations are left alone.

    :rtype: main.types.CompositeSourcedBibliographicItem
    """
    raise NotImplementedError()


DocIDTuple = Tuple[Tuple[str, str], Tuple[str, str]]


def build_search_results(
    refs: QuerySet[RefData],
) -> List[FoundItem]:
    """Given a :class:`django.db.models.query.QuerySet`
    of :class:`~.models.RefData` entries, builds a list
    of :class:`~.types.FoundItem` objects
    by merging ``RefData`` instances that share
    their primary document identifier.

    Takes care of merging search headline annotations, if any.

    :param django.db.models.query.QuerySet[RefData] refs: found refs
    :rtype: List[FoundItem]
    """

    # Groups refs by primary ID
    # (in absence of such, a ref will go alone under its first ID)
    refs_by_primary_id: Dict[str, List[int]] = {}

    results: List[FoundItem] = []

    for idx, ref in enumerate(refs):
        suitable_ids: List[DocID] = as_list([
            DocID(**id)
            for id in ref.body.get('docid', [])
            if 'id' in id and 'scope' not in id and 'type' in id
        ])

        # TODO: Skip ``fallback_formattedref`` cases with #196
        fallback_formattedref = (
            ref.body.
            get('formattedref', {}).
            get('content', None))
        if suitable_ids:
            primary_id = get_primary_docid(suitable_ids)
            if primary_id:
                refs_by_primary_id.setdefault(primary_id.id, [])
                refs_by_primary_id[primary_id.id].append(idx)
            else:
                refs_by_primary_id[suitable_ids[0].id] = [idx]
        elif fallback_formattedref: #196
            refs_by_primary_id[fallback_formattedref] = [idx]

    for _docid, ref_indexes in refs_by_primary_id.items():
        refs_to_merge: List[RefData] = [refs[idx] for idx in ref_indexes]

        if len(refs_to_merge) > 0:
            headlines = set([
                getattr(r, 'headline', '')
                for r in refs_to_merge
            ])
            found_item, valid = typeCast(
                Tuple[FoundItem, bool],
                compose_bibitem(refs_to_merge, _docid, strict=False))
            found_item.headline = ' … '.join(headlines)
            results.append(found_item)

    return results


def get_indexed_item(
    dataset_id: str,
    ref: str,
    strict=True,
) -> IndexedBibliographicItem:
    """Retrieves a bibliographic item by :term:`reference`
    from an indexed internal dataset.

    :param bool strict: see :ref:`strict-validation`
    :rtype: IndexedBibliographicItem
    :raises RefNotFoundError: either reference or requested format not found
    :raises pydantic.ValidationError:
        if ``strict`` is True and ``BibliographicItem`` instance
        did not validate at construction.
    """

    ref = get_indexed_ref_by_query(dataset_id, Q(ref__iexact=ref))
    bibitem, errors = construct_bibitem(ref.body, strict)

    return IndexedBibliographicItem(
        source=get_source_meta(dataset_id),
        indexed_object=get_indexed_object_meta(dataset_id, ref.ref),
        validation_errors=errors,
        bibitem=bibitem,
    )


def get_indexed_ref_by_query(
    dataset_id: str,
    query: Q,
) -> RefData:
    """Uses query to retrieve a :class:`~main.models.RefData`
    by :term:`reference`
    from an indexed internal dataset.

    :param django.db.models.Q query: query
    :rtype: main.models.RefData
    :raises RefNotFoundError: either reference or requested format not found
    """

    try:
        return RefData.objects.get(
            query &
            Q(dataset__iexact=dataset_id))
    except RefData.DoesNotExist:
        raise RefNotFoundError(
            "Cannot find matching reference in given dataset",
            repr(Q))
    except RefData.MultipleObjectsReturned:
        raise RefNotFoundError(
            "Multiple references match query in given dataset",
            repr(Q))
