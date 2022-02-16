"""Query-related utilities."""

from typing import Callable, Union, List, Dict, Any, Optional
import logging

from django.db.models.query import QuerySet
from django.db.utils import ProgrammingError, DataError

from pydantic import ValidationError

from bib_models.models.bibdata import BibliographicItem, DocID
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
    Merges retrieved refs into a composite item.

    :param primary_id:
        :attr:`main.types.CompositeSourcedBibliographicItem.primary_docid`

    :param bool strict:
        Throw if an item failed Pydantic validation.
        Is True by default. Can be set to False
        if it’s acceptable for data structure to be fuzzy
        (e.g., when it’s to be displayed and not
        to be manipulated programmatically).

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
    """Extracts a primary document identifier from a list of objects
    as it appears under 'docid' in deserialized Relaton data.
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
            id,
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
