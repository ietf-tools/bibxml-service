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

from management.datasets import get_source_meta, get_indexed_object_meta
from common.util import as_list
from bib_models.models import BibliographicItem
from bib_models.dataclasses import DocID
from bib_models.merger import bibitem_merger

from .types import IndexedBibliographicItem, CompositeSourcedBibliographicItem
from .exceptions import RefNotFoundError
from .models import RefData


log = logging.getLogger(__name__)


def query_suppressing_user_input_error(query: Callable[[], QuerySet[RefData]]) \
        -> Union[QuerySet[RefData], None]:
    """Evaluates provided query and tries to suppress any error
    that may result from bad user input.
    """
    try:
        qs = query()
        len(qs)  # Evaluate
    except (ProgrammingError, DataError) as e:
        if not is_benign_user_input_error(e):
            raise
        else:
            return None
    else:
        return qs


def is_benign_user_input_error(exc: Union[ProgrammingError, DataError]) \
        -> bool:
    """The service allows the user to make complex queries directly
    using PostgreSQL’s various JSON path and/or regular expression
    matching functions.

    As it appears impossible to validate a query in advance,
    we allow PostgreSQL to throw and check the thrown exception
    for certain substrings that point to input syntax issues.
    Those can then be suppressed and user would be able to edit the query.

    We do not want to accidentally suppress actual error states,
    which would bubble up under the same exception classes.

    Note that user input must obviously still be properly escaped.
    Escaping is delegated to Django’s ORM, see :mod:`main.indexed`.
    """

    err = repr(exc)
    return any((
        "invalid regular expression" in err,
        "syntax error" in err and "jsonpath input" in err,
        "unexpected end of quoted string" in err and "jsonpath input" in err,
    ))


def list_refs(dataset_id: str) -> QuerySet[RefData]:
    return RefData.objects.filter(dataset__iexact=dataset_id)


def search_refs_json_repr_match(text: str, limit=None) -> QuerySet[RefData]:
    """Uses given string to search across serialized JSON representations
    of Relaton citation data.

    Supports PostgreSQL websearch operators like quotes, plus, minus, OR, AND.
    """
    limit = limit or getattr(settings, 'DEFAULT_SEARCH_RESULT_LIMIT', 100)

    return (
        RefData.objects.
        annotate(search=SearchVector(Cast('body', TextField()))).
        filter(search=SearchQuery(text, search_type='websearch')).
        only('ref', 'dataset', 'body')[:limit])


def search_refs_relaton_struct(
        *objs: Union[Dict[Any, Any], List[Any]],
        limit=None) -> QuerySet[RefData]:
    """Uses PostgreSQL’s JSON containment query
    to find bibliographic items containing any of given structures.

    .. note:: This search is case-sensitive.

    .. seealso:: PostgreSQL docs on ``@>`` operator.

    :returns: RefData where Relaton body contains
              at least one of given ``obj`` structures.
    :rtype: Queryset[RefData]
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
        only('ref', 'dataset', 'body')[:limit])


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

    :param int limit: Converts to DB ``LIMIT``.

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

    :rtype: Queryset[RefData]
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

    qs = RefData.objects.filter(id__in=final_query)

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


def list_doctypes() -> List[Tuple[str, str]]:
    """Lists all distinct ``docid[*].doctype`` values among citation data.

    Returns a list of 2-tuples (document type, example document ID).
    """
    return [
        (i.doctype, i.sample_id)
        for i in (
            RefData.objects.
            # order_by('?').  # This may be inefficient as dataset grows
            raw('''
                select distinct on (doctype) id, doctype, sample_id
                from (
                    select id, jsonb_array_elements_text(
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
                ) as item
                ''')
        )
    ]


def search_refs_for_docids(*ids: Union[DocID, str]) \
        -> QuerySet[RefData]:

    # Exact & fast
    struct_queries: List[Any] = [
        struct
        for (id, id_type) in (
            (id.id, id.type) if isinstance(id, DocID) else (id, None)
            for id in ids
        )
        for struct in (
            {'docid': [{'id': id, 'type': id_type}]}
            if id_type else {'docid': [{'id': id}]},
            # {'docid': {'id': id, 'type': id_type}}
            # if id_type else {'docid': {'id': id}},
        )
    ]
    refs = search_refs_relaton_struct(
        *struct_queries,
        limit=15,
    )

    if len(refs) < 1:
        # Less exact, case-insensitive, slower
        jsonpath_queries = [
            # To exclude untyped:
            # f'@.id like_regex {docid} && exists (@.type)' % docid
            {'docid[*]':
                f'@.type like_regex {id} && @.id like_regex {id_type}'
                if id_type else f'@.id like_regex {id}'}
            for (id, id_type) in ((
                '"(?i)^%s$"' % re.escape(
                    id.id
                    if isinstance(id, DocID) else id
                ),
                '"(?i)^%s$"' % re.escape(id.type)
                if getattr(id, 'type', None) else None,
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


def build_citation_for_docid(id: str, id_type: Optional[str] = None) -> \
        CompositeSourcedBibliographicItem:
    """Returns a ``BibliographicItem`` constructed from ``RefData`` instances
    that matched given document identifier (``docid.id`` value).

    Returns complete citation representation contained in ``body``.

    If multiple refs were found, their citation data are merged.
    (At most 10 found refs are considered, which is already atypically many.)

    :returns BibliographicItem: a :class:`bib_models.BibliographicItem`
                                instance.
    :raises RefNotFoundError: if no matching refs were found.
    """

    # Retrieve pre-indexed refs
    refs = query_suppressing_user_input_error(
        lambda: search_refs_for_docids(DocID(id, id_type) if id_type else id)
    ) or []

    if len(refs) < 1:
        raise RefNotFoundError("Not found in indexed sources by docid", id)

    docids = [
        DocID(id=docid['id'], type=docid['type'])
        for ref in refs
        for docid in as_list(ref.body['docid'])
        # Require id and type, but no scope:
        if (docid.get('id', None)
            and docid.get('type', None)
            and not docid.get('scope', None)
            # Exclude originally given ID:
            and (docid['id'] != id or docid['type'] != id_type))
    ]

    # Retrieve bibliographic items with intersecting identifiers
    additional_refs = query_suppressing_user_input_error(
        lambda: search_refs_for_docids(*docids)
    ) or []

    refs = [*refs, *additional_refs]

    base: Dict[str, Any] = {}
    # Merged bibitems

    sources: Dict[str, IndexedBibliographicItem] = {}
    # Their sources

    if len(refs) == 1:
        ref = refs[0]

        source = get_source_meta(ref.dataset)
        obj = get_indexed_object_meta(ref.dataset, ref.ref)
        sourced_id = f'{ref.ref}@{source.id}'

        base.update(ref.body)
        try:
            bibitem = BibliographicItem(**ref.body)
            validation_errors = []
        except ValidationError as e:
            log.warn(
                "Incorrect bibliographic item format: %s, %s",
                ref.ref, e)
            bibitem = BibliographicItem.construct(**ref.body)
            validation_errors = [str(e)]
        sources[sourced_id] = IndexedBibliographicItem(
            indexed_object=obj,
            source=source,
            bibitem=bibitem,
            validation_errors=validation_errors,
        )

    elif len(refs) > 1:
        seen_types_by_id: Dict[str, str] = {}

        for ref in refs:
            source = get_source_meta(ref.dataset)
            obj = get_indexed_object_meta(ref.dataset, ref.ref)
            sourced_id = f'{ref.ref}@{source.id}'

            for _docid in ref.body.get('docid', []):
                # Identifier sanity check
                _type = _docid.get('type', '').strip()
                _id = _docid.get('id', None)
                _scope = _docid.get('scope', None)
                if not _id:
                    raise RefNotFoundError(
                        "Encountered item missing docid.id", id)
                if not isinstance(_type, str) or len(_type) < 1:
                    raise RefNotFoundError(
                        "Encountered item missing docid.type", id)

                # Sanity check that ID-IDs don’t clash across types,
                # otherwise we are dealing with different bibliographic items
                # that should not be merged
                if _scope is None:
                    seen_type = seen_types_by_id.get(_id, _type)
                    if seen_type != _type:
                        log.warning(
                            "Mismatching docid.type/docid.id when merging: "
                            "ID %s, got type %s, "
                            "but already seen type %s for this ID",
                            _id, _type, seen_type)
                        raise RefNotFoundError(
                            "Encountered items "
                            "with incompatible document identifier types",
                            id)
                    seen_types_by_id[_id] = _type

            bibitem_merger.merge(base, ref.body)
            try:
                bibitem = BibliographicItem(**ref.body)
                validation_errors = []
            except ValidationError as e:
                log.warn(
                    "Incorrect bibliographic item format: %s, %s",
                    ref.ref, e)
                bibitem = BibliographicItem.construct(**ref.body)
                validation_errors = [str(e)]

            sources[sourced_id] = IndexedBibliographicItem(
                indexed_object=obj,
                source=source,
                bibitem=bibitem,
                validation_errors=validation_errors,
            )

    composite: Dict[str, Any] = {
        **base,
        'sources': sources,
    }
    return CompositeSourcedBibliographicItem.construct(**composite)

    # if any([len(s.validation_errors or []) > 0
    #         for s in sources.values()]):
    #     return CompositeSourcedBibliographicItem.construct(**composite)
    # else:
    #     try:
    #         return CompositeSourcedBibliographicItem(**base)
    #     except ValidationError:
    #         log.exception(
    #             "Failed to validate composite sourced bibliographic item %s",
    #             id)
    #         return CompositeSourcedBibliographicItem.construct(**composite)


DocIDTuple = Tuple[Tuple[str, str], Tuple[str, str]]


def build_search_results(
    refs: QuerySet[RefData],
    order_by: Optional[str] = None,
) -> List[IndexedBibliographicItem]:
    """Given a :class:`QuerySet` of :class:`RefData` entries,
    build a list of :class:`SourcedBibliographicItem` objects
    by merging ``RefData`` with intersecting document identifiers.
    """

    # Tracks which document ID is represented by which source references
    # (referenced by indices in the ``refs`` list)
    refs_by_docid: Dict[FrozenSet[DocIDTuple], List[int]] = {}

    # Tracks which document IDs refer to the same bibliographic item
    # For bibliographic items that have at least one document ID in common,
    # all their document IDs are considered aliases to each other.
    alias_docids: Dict[FrozenSet[DocIDTuple], Set[DocIDTuple]] = {}

    results: List[CompositeSourcedBibliographicItem] = []

    for idx, ref in enumerate(refs):
        docid_tuples: FrozenSet[DocIDTuple] = frozenset(
            typeCast(DocIDTuple, tuple(docid.items()))
            for docid in as_list(ref.body['docid'])
            # Exclude identifiers with scope or missing id/type
            if all([
                docid.get('type', None),
                docid.get('id', None),
                not docid.get('scope', None)])
        )
        for id in docid_tuples:
            id_tuple: FrozenSet[DocIDTuple] = frozenset([id])
            refs_by_docid.setdefault(id_tuple, [])
            alias_docids.setdefault(id_tuple, set())
            refs_by_docid[id_tuple].append(idx)
            alias_docids[id_tuple].update(docid_tuples)

    processed_docids = set[DocIDTuple]()

    for _docid, ref_indexes in refs_by_docid.items():
        docid, = _docid
        if docid in processed_docids:
            # This identifier was already processed as an alias
            continue
        # Don’t process this identifier as an alias next time
        processed_docids.add(docid)

        aliases: Set[DocIDTuple] = alias_docids.get(_docid, set())

        # Refs that contain bibliographic data
        # for this document identifier
        ref_idxs = refs_by_docid.get(_docid, [])

        # For any aliases that were not yet processed,
        # add refs that contain their bibliographic data
        # to refs for this document identifier
        # and exclude from processing
        for alias_docid in (aliases - processed_docids):
            processed_docids.add(alias_docid)
            ref_idxs.extend(
                refs_by_docid.get(
                    frozenset([alias_docid]),
                    []))

        refs_to_merge: Set[RefData] = set([refs[idx] for idx in ref_idxs])

        if len(refs_to_merge) > 0:
            base: Dict[str, Any] = {'sources': {}}
            sources: Dict[str, IndexedBibliographicItem] = {}
            for ref in refs_to_merge:
                if hasattr(ref, 'headline'):
                    base['headline'] = ref.headline

                bibitem_merger.merge(base, ref.body)

                source = get_source_meta(ref.dataset)
                obj = get_indexed_object_meta(ref.dataset, ref.ref)
                sourced_id = f'{ref.ref}@{source.id}'
                try:
                    bibitem = BibliographicItem(**ref.body)
                    validation_errors = []
                except ValidationError as e:
                    bibitem = BibliographicItem.construct(**ref.body)
                    validation_errors = [str(e)]
                sources[sourced_id] = IndexedBibliographicItem(
                    indexed_object=obj,
                    source=source,
                    bibitem=bibitem,
                    validation_errors=validation_errors,
                )
            results.append(CompositeSourcedBibliographicItem.construct(**base))

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
