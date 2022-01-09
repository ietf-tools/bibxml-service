import json
from typing import Dict, List, Union, Tuple, Any

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models.query import QuerySet, Q
from django.db.models import TextField
from django.db.models.functions import Cast

from .exceptions import RefNotFoundError
from .models import RefData

from bib_models import BibliographicItem
from bib_models.merger import bibitem_merger

# TODO: Obsolete, now that we gave up on multi-DB approach
RefDataManager = RefData.objects
from .types import DocID
from .models import RefData


def list_refs(dataset_id) -> QuerySet[RefData]:
    return RefDataManager.filter(dataset__iexact=dataset_id)


def search_refs_json_repr_match(text: str) -> QuerySet[RefData]:
    """Uses given string to search across serialized JSON representations
    of Relaton citation data.

    Supports typical websearch operators like quotes, plus, minus, OR, AND.
    """
    return (
        RefDataManager.
        annotate(search=SearchVector(Cast('body', TextField()))).
        filter(search=SearchQuery(text, search_type='websearch')))


def search_refs_relaton_struct(
        *objs: Union[Dict[Any, Any], List[Any]]) -> QuerySet[RefData]:
    """Uses PostgreSQL’s JSON containment query.

    Returns citations which Relaton structure contains
    at least one of given ``obj`` structures (they are OR'ed).

    .. seealso:: PostgreSQL docs on ``@>`` operator.
    """
    subqueries = ['body @> %s::jsonb' for obj in objs]
    query = 'SELECT * FROM api_ref_data WHERE %s' % ' OR '.join(subqueries)
    return (
        RefDataManager.
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
        for fieldpath, query in fields.items():
            interpolated_param_key = '{idx}_{fieldpath}'.format(
                idx=idx,
                fieldpath=fieldpath)

            if exact:
                interpolated_params[interpolated_param_key] = \
                    '$.{fieldpath} ? ({query})'.format(
                        fieldpath=fieldpath,
                        query=query)
                anded_queries.append(
                    'body @? %({key})s'.format(
                        key=interpolated_param_key,
                    ),
                )

            else:
                interpolated_params[interpolated_param_key] = query
                if fieldpath == '':
                    # Below query:
                    #
                    # 1) constructs one “normal” tsvector
                    #    using JSON values only,
                    # 2) serializes JSON to text
                    #    with some post-processing
                    #    (currently replaing slashes with spaces, thus
                    #    breaking any string with a slash into 2 tokens),
                    #    turns that text into a tsvector but then
                    #    subtracts all lexemas corresponding to JSON keys,
                    # 3) applies the websearch query
                    #    to the union of both above vectors.
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
                            ts_delete(
                                to_tsvector(
                                    'english',
                                    translate(body::text, '/', ' ')
                                ),
                                tsvector_to_array(
                                    jsonb_to_tsvector(
                                        'english',
                                        body,
                                        '["key"]'
                                    )
                                )
                            )
                        ) @@ websearch_to_tsquery('english', %({key})s)
                    '''
                else:
                    tpl = '''
                        to_tsvector(
                            'english',
                            jsonb_extract_path(body, {fieldpath})
                        ) @@ websearch_to_tsquery('english', %({key})s)
                    '''
                anded_queries.append(
                    tpl.format(
                        # {fieldpath} is properly escaped,
                        # callers must not pass user input here.
                        fieldpath=','.join([
                            "'%s'" % part
                            for part in fieldpath.split('.')]),
                        key=interpolated_param_key,
                    ),
                )
        ored_queries.append('(%s)' % ' AND '.join(anded_queries))

    final_query = '''
        SELECT * FROM api_ref_data WHERE %s
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
            RefDataManager.
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


def build_citation_for_docid(id: DocID) -> BibliographicItem:
    """Returns a ``BibliographicItem`` constructed from ``RefData`` instances
    that matched given document identifier.

    Returns complete citation representation contained in ``body``.
    If multiple refs were found, their citation data are merged.

    :returns BibliographicItem: a :class:`bib_models.BibliographicItem`
                                instance.
    :raises RefNotFoundError: if no matching refs were found.
    """
    doctype = json.dumps(id['type'])
    docid = json.dumps(id['id'])

    refs = search_refs_relaton_field({
        'docid[*]': '@.type == %s && @.id == %s' % (
            doctype,
            docid,
        ),
    }, exact=True)

    if len(refs) == 1:
        # print("Obtained raw ref", json.dumps(refs[0].body, indent=4))
        return BibliographicItem(**refs[0].body)

    elif len(refs) > 1:
        base: Dict[str, Any] = {}
        for ref in refs:
            bibitem_merger.merge(base, BibliographicItem(**ref.body).dict())
        return BibliographicItem(**base)

    else:
        raise RefNotFoundError("Not found in indexed sources by docid", id)


def get_indexed_ref(dataset_id, ref, format='relaton'):
    """Retrieves citation from static indexed dataset.

    :param str format: "bibxml" or "relaton"
    :returns dict: if format is "relaton", a :class:`dict`.
    :returns str: if format is "bibxml", an XML string.
    :raises RefNotFoundError: either reference or requested format not found
    """

    return get_indexed_ref_by_query(dataset_id, Q(ref__iexact=ref), format)


def get_indexed_ref_by_query(dataset_id, query: Q, format='relaton'):
    """Retrieves citation from static indexed dataset.

    :param str format: "bibxml" or "relaton"
    :param django.db.models.Q query: query
    :returns: reference in specified format, if available
    :rtype: dict or str, depending on format
    :raises RefNotFoundError: either reference or requested format not found
    """

    if format not in ['relaton', 'bibxml']:
        raise ValueError("Unknown citation format requested")

    try:
        result = RefDataManager.get(
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
