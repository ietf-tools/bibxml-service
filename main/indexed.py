import logging
import json
from typing import cast as typeCast, Set, FrozenSet, Optional
from typing import Dict, List, Union, Tuple, Any

from pydantic import ValidationError

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models.query import QuerySet, Q
from django.db.models import TextField
from django.db.models.functions import Cast


from common.util import as_list
from bib_models import BibliographicItem
from bib_models.merger import bibitem_merger

from .types import SourcedBibliographicItem
from .exceptions import RefNotFoundError
from .models import RefData


log = logging.getLogger(__name__)


def list_refs(dataset_id) -> QuerySet[RefData]:
    return RefData.objects.filter(dataset__iexact=dataset_id)


def search_refs_json_repr_match(text: str) -> QuerySet[RefData]:
    """Uses given string to search across serialized JSON representations
    of Relaton citation data.

    Supports PostgreSQL websearch operators like quotes, plus, minus, OR, AND.
    """
    return (
        RefData.objects.
        annotate(search=SearchVector(Cast('body', TextField()))).
        filter(search=SearchQuery(text, search_type='websearch')))


def search_refs_relaton_struct(
        *objs: Union[Dict[Any, Any], List[Any]]) -> QuerySet[RefData]:
    """Uses PostgreSQL’s JSON containment query
    to find bibliographic items containing given structure.

    .. seealso:: PostgreSQL docs on ``@>`` operator.

    :returns: RefData where Relaton body contains
              at least one of given ``obj`` structures (they are OR'ed).
    :rtype: Queryset[RefData]
    """
    subqueries = ['body @> %s::jsonb' for obj in objs]
    query = 'SELECT * FROM api_ref_data WHERE %s' % ' OR '.join(subqueries)
    return (
        RefData.objects.
        raw(query, [json.dumps(obj) for obj in objs]))


def search_refs_relaton_field(
        *field_queries: Dict[str, str],
        exact=False) -> QuerySet[RefData]:
    """
    Each of ``field_queries`` should be a dictionary of the following shape::

        { '<field spec>': '<query>', '<field spec>': '<query>', ... }

    .. important:: Do **not** pass user input directly in field specs
                   if you don’t set ``exact`` to ``True``.

    The ``exact`` flag applies to all ``field_queries``.

    - If ``exact`` is ``False`` (default),
      wildcards in field paths are not allowed,
      and object at each field path is passed through ``to_tsvector()``
      while corresponding value is passed through ``::tsquery``
      for fuzzy matching.

      Example::

          { 'docid': 'IEEE', 'keyword': 'something' }

      Empty field spec is treated specially, matching the whole body::

          { '': 'string anywhere in body' }

    - If ``exact`` is ``True``, field path specification
      can use PostgreSQL’s ``jsonpath``
      with wildcards (e.g., ``somearray[*].someitem``),
      and values must be PostgreSQL JSON queries like this: ``@ == \"%s\"``
      (where ``@`` references given field path).

      There is more flexibility, but it is required to be exact
      when specifying queries. Incorrect syntax will cause
      a ``ProgrammingError``, which this function won’t catch.

      Example::

          {
              'docid[*]': '@.type == "IEEE" && @.id == "some-ieee-id"',
              'keyword[*]': '@ == "something"',
          }

      Note that the above example will not match a document
      where keyword is not a list, but a string ``"something"``.

    Queries within each dictionary of ``field_queries`` are AND’ed,
    and resulting queries
    (if you pass more than one dict in ``field_queries``)
    are OR’ed.

    :rtype: Queryset[RefData]
    """

    ored_queries = []
    interpolated_params: Dict[str, Union[str, int]] = {}

    for idx, fields in enumerate(field_queries):
        anded_queries = []
        for fieldspec, query in fields.items():
            interpolated_param_key = '{idx}_{fieldpath}'.format(
                idx=idx,
                fieldpath=fieldspec)

            if exact:
                interpolated_params[interpolated_param_key] = \
                    '$.{fieldpath} ? ({query})'.format(
                        fieldpath=fieldspec,
                        query=query)
                anded_queries.append(
                    'body @? %({key})s'.format(
                        key=interpolated_param_key,
                    ),
                )

            else:
                interpolated_params[interpolated_param_key] = query
                if fieldspec == '':
                    # Below query creates a tsvector from the entire body,
                    # and then adds a tsvector produced from body.docid as text
                    # with spaces instead of slashes to tokenize slash-separated
                    # parts of IDs.
                    #
                    # (This works around PostgreSQL’s text search
                    # not splitting tokens on slashes.
                    #
                    # With simple `to_tsvector(bibitem_json)`,
                    # if you search for NBS.IR.82-2601p1 you won’t match
                    # `{type: 'DOI', id: '10.6028/NBS.IR.82-2601p1'}`
                    # as 10.6028/NBS.IR.82-2601p1 is a single token.
                    #
                    # Another way to work around this
                    # could be by tuning DB configuration.)
                    tpl = '''
                        (
                            jsonb_to_tsvector(
                                'english',
                                body,
                                '["string", "numeric", "boolean"]'
                            ) ||
                            to_tsvector(
                                'english',
                                translate((body->'docid')::text, '/', ' ')
                            )
                        ) @@ websearch_to_tsquery('english', %({key})s)
                    '''
                    anded_queries.append(tpl.format(
                        key=interpolated_param_key,
                    ))
                else:
                    tpl = '''
                        to_tsvector(
                            'english',
                            jsonb_build_array({json_selectors})
                        ) @@ websearch_to_tsquery('english', %({key})s)
                    '''
                    anded_queries.append(tpl.format(
                        key=interpolated_param_key,
                        json_selectors=', '.join([
                            'jsonb_extract_path(body, {fieldpath})'.format(
                                # {fieldpath} is not properly escaped,
                                # callers must not pass user input here.
                                fieldpath=','.join([
                                    "'%s'" % part
                                    for part in fieldpath.split('.')]),
                            ) for fieldpath in fieldspec.split(',')]),
                    ))
        ored_queries.append('(%s)' % ' AND '.join(anded_queries))

    final_query = '''
        SELECT id, body, ref, dataset FROM api_ref_data WHERE %s
    ''' % ' OR '.join(ored_queries)

    # print("search_refs_relaton_field: final query", final_query, interpolated_params)

    return RefData.objects.raw(final_query, interpolated_params)


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
                '''))]


def build_citation_for_docid(id: str, id_type: Optional[str] = None) -> \
        SourcedBibliographicItem:
    """Returns a ``BibliographicItem`` constructed from ``RefData`` instances
    that matched given document identifier (``docid.id`` value).

    Returns complete citation representation contained in ``body``.
    If multiple refs were found, their citation data are merged.

    :returns BibliographicItem: a :class:`bib_models.BibliographicItem`
                                instance.
    :raises RefNotFoundError: if no matching refs were found.
    """
    docid = json.dumps('(?i)^%s$' % id)

    if id_type:
        doctype = json.dumps('(?i)^%s$' % id_type)
        query = '@.type like_regex %s && @.id like_regex %s' % (
            doctype,
            docid,
        )
    else:
        query = '@.id like_regex %s' % docid
        # To exclude untyped:
        # query = '@.id like_regex %s && exists (@.type)' % docid

    refs = search_refs_relaton_field({'docid[*]': query}, exact=True)

    base: Dict[str, Any] = {'sources': {}}

    if len(refs) == 1:
        # print("Obtained raw ref", json.dumps(refs[0].body, indent=4))
        ref = refs[0]
        base.update(ref.body)
        base['sources'][ref.dataset] = {
            'ref': ref.ref,
            'bibitem': ref.body,
        }
        try:
            BibliographicItem(**ref.body)
        except ValidationError as e:
            log.warn(
                "Incorrect bibliographic item format: %s, %s",
                ref.ref, e)
            base['sources'][ref.dataset]['validation_errors'] = str(e)

    elif len(refs) > 1:
        seen_docids_by_type: Dict[str, str] = {}
        for ref in refs:
            bibitem = ref.body

            for _docid in bibitem.get('docid', []):
                # Identifier sanity check
                _type = _docid.get('type', '').strip()
                _id = _docid.get('id', None)
                _scope = _docid.get('scope', None)
                if not _id:
                    raise RefNotFoundError(
                        "Encountered a ref missing docid.id", id)
                if not isinstance(_type, str) or len(_type) < 1:
                    raise RefNotFoundError(
                        "Encountered a ref missing docid.type", id)

                # Sanity check that ID-IDs don’t clash across types,
                # otherwise we are dealing with different bibliographic items
                # that should not be merged
                if _scope is None:
                    if seen_docids_by_type.get(_type, _id) != _id:
                        raise RefNotFoundError(
                            "Mismatching docid.type/docid.id when merging",
                            id)
                    seen_docids_by_type[_type] = _id

            bibitem_merger.merge(base, bibitem)
            base['sources'][ref.dataset] = {
                'ref': ref.ref,
                'bibitem': ref.body,
            }
            try:
                BibliographicItem(**ref.body)
            except ValidationError as e:
                log.warn(
                    "Incorrect bibliographic item format: %s, %s",
                    ref.ref, e)
                base['sources'][ref.dataset]['validation_errors'] = str(e)
    else:
        raise RefNotFoundError("Not found in indexed sources by docid", id)

    if any([len(s.get('validation_errors', [])) > 0
            for s in base.get('sources', {}).values()]):
        return SourcedBibliographicItem.construct(**base)
    else:
        try:
            return SourcedBibliographicItem(**base)
        except ValidationError:
            log.exception(
                "Failed to validate final sourced bibliographic item",
                id)
            return SourcedBibliographicItem.construct(**base)


DocIDTuple = Tuple[Tuple[str, str], Tuple[str, str]]


def build_search_results(
    refs: QuerySet[RefData],
    order_by: Optional[str] = None,
) -> List[SourcedBibliographicItem]:
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

    results: List[SourcedBibliographicItem] = []

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
            for ref in refs_to_merge:
                bibitem_merger.merge(base, ref.body)
                base['sources'][ref.dataset] = {
                    'ref': ref.ref,
                    'bibitem': ref.body,
                }
                try:
                    BibliographicItem(**ref.body)
                except ValidationError as e:
                    base['sources'][ref.dataset]['validation_errors'] = str(e)
            results.append(SourcedBibliographicItem.construct(**base))

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
