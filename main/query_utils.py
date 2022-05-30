"""Query-related utilities."""

from typing import Callable, Union, List, Dict, Any, Optional
import logging

from django.db.models.query import QuerySet
from django.db.utils import ProgrammingError, DataError

from pydantic import ValidationError

from bib_models import BibliographicItem, DocID
from bib_models.merger import bibitem_merger

from .models import RefData
from .sources import get_source_meta, get_indexed_object_meta
from .exceptions import RefNotFoundError
from .types import CompositeSourcedBibliographicItem
from .types import IndexedBibliographicItem


__all__ = (
    'merge_refs',
    'get_primary_docid',
    'get_docid_struct_for_search',
    'query_suppressing_user_input_error',
    'is_benign_user_input_error',
)


log = logging.getLogger(__name__)


def merge_refs(
    refs: List[RefData],
    primary_id: Optional[str] = None,
    strict: bool = True,
) -> CompositeSourcedBibliographicItem:
    """
    Converts multiple physical ``RefData`` instances
    into a single logical bibliographic item.

    This function assumes that you have ensured to collect ``RefData``
    instances that represent the same bibliographic item
    using ``primary_id`` as shared docid.

    :param django.db.models.query.QuerySet[RefData] refs:
       References to use.

       .. note::

          Should be ordered by date, latest document first.

    :param primary_id:
        :attr:`main.types.CompositeSourcedBibliographicItem.primary_docid`

    :param bool strict: see :ref:`strict-validation`

    :rtype: main.types.CompositeSourcedBibliographicItem
    """

    base: Dict[str, Any] = {}
    # Merged bibitems

    sources: Dict[str, IndexedBibliographicItem] = {}
    # Their sources

    for ref in refs:
        source = get_source_meta(ref.dataset)
        obj = get_indexed_object_meta(ref.dataset, ref.ref)
        sourced_id = f'{ref.ref}@{source.id}'

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
        'primary_docid': primary_id,
    }
    if strict is not False:
        return CompositeSourcedBibliographicItem(**composite)
    else:
        try:
            return CompositeSourcedBibliographicItem(**composite)
        except ValidationError:
            log.exception(
                "Failed to validate composite sourced bibliographic item "
                "with primary docid %s "
                "(suppressed with strict=False)",
                primary_id)
            return CompositeSourcedBibliographicItem.construct(**composite)


def resolve_relations(
    items: List[BibliographicItem],
) -> Dict[str, BibliographicItem]:
    """
    For every given :class:`~relaton.models.bibdata.BibliographicItem`
    of ``items``, scans for any relations that are ``formattedref``-only links.

    Fetches all referenced documents and returns a dictionary
    that maps each ``formattedref``
    to corresponding :class:`~relaton.models.bibdata.BibliographicItem`.

    The resulting dictionary can be used with :func:`.hydrate_bibitem()`.
    """
    raise NotImplementedError()


def hydrate_bibitem(
    item: BibliographicItem,
    resolved_relations: Dict[str, BibliographicItem],
) -> BibliographicItem:
    """
    Given a :class:`~relaton.models.bibdata.BibliographicItem` that:

    1. Possibly contains ``formattedref``-only relations
    2. Possibly itself is just a ``formattedref``

    Tries to replace all ``formattedref`` occurrences with fully fledged
    bibliographic items:

    1. For relations, tries to retrieve all documents
       referenced via ``formattedref``
       via their ``primary`` docid in one query.
    2. If item itself has a ``formattedref`` and is missing vital metadata,
       such as title, attempts to fill in that metadata from relations.

    :param dict resolved_relations:
        If supplied, no DB queries are made
        and the dictionary is used for resolving relations.
        If caller is resolving many items, it may pre-fetch all relations
        referenced via ``formattedref`` ahead of time.

    :returns:
        The same logical bibliographic item, ideally with fewer formattedrefs
        and more suitable for displaying to the user.
    """
    raise NotImplementedError()


def get_docid_struct_for_search(id: DocID) -> Dict[str, Any]:
    """Converts a given ``DocID`` instance into a structure
    suitable for being passed
    to :func:`~main.query.search_refs_relaton_struct()`.
    """

    struct: Dict[str, Any] = {'id': id.id, 'type': id.type}
    if id.primary:
        struct['primary'] = True
    return struct


def get_primary_docid(raw_ids: List[Dict[str, Any]]) -> Optional[DocID]:
    """Extracts a single primary document identifier from a list of objects
    as it appears under “docid” in deserialized Relaton data.

    Logs a warning if more than one primary identifier was found.

    :rtype: relaton.models.bibdata.DocID or None
    """

    primary_docids: List[DocID] = [
        DocID(id=docid['id'], type=docid['type'], primary=True)
        for docid in raw_ids
        if all([
            docid.get('primary', False),
            # As a further sanity check, require id and type, but no scope:
            docid.get('id', None),
            docid.get('type', None),
            not docid.get('scope', None),
        ])
    ]

    deduped = set([frozenset([id.id, id.type]) for id in primary_docids])

    if len(deduped) != 1:
        log.warn(
            "build_citation_by_docid: unexpected number of primary docids "
            "found for %s: %s",
            raw_ids,
            len(primary_docids))

    try:
        return primary_docids[0]
    except IndexError:
        return None


def query_suppressing_user_input_error(
    query: Callable[[], QuerySet[RefData]],
) -> Union[QuerySet[RefData], None]:
    """Force-evaluates (!) the provided query and tries to suppress any error
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
    Escaping is delegated to Django’s ORM,
    see e.g. :func:`.search_refs_relaton_field`.
    """

    err = repr(exc)
    return any((
        "invalid regular expression" in err,
        "syntax error" in err and "jsonpath input" in err,
        "unexpected end of quoted string" in err and "jsonpath input" in err,
    ))
