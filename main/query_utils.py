"""Query-related utilities."""

from typing import Callable, Union, Sequence, Dict, Any, Optional, Tuple
import logging

from django.db.models.query import QuerySet
from django.db.utils import ProgrammingError, DataError

from bib_models import construct_bibitem, DocID
from bib_models.merger import bibitem_merger

from .models import RefData
from .sources import get_source_meta, get_indexed_object_meta
from .types import CompositeSourcedBibliographicItem
from .types import IndexedBibliographicItem


__all__ = (
    'compose_bibitem',
    'get_docid_struct_for_search',
    'query_suppressing_user_input_error',
    'is_benign_user_input_error',
)


log = logging.getLogger(__name__)


def compose_bibitem(
    refs: Sequence[RefData],
    primary_id: Optional[str] = None,
    strict: bool = True,
) -> Tuple[CompositeSourcedBibliographicItem, bool]:
    """
    Converts multiple physical ``RefData`` instances,
    possibly from different bibliographic data sources,
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

    :returns: 2-tuple (main.types.CompositeSourcedBibliographicItem, is_valid)
    """

    base: Dict[str, Any] = {}
    # Merged bibitems

    sources: Dict[str, IndexedBibliographicItem] = {}
    # Their sources

    validation_errors_encountered = False

    for ref in refs:
        source = get_source_meta(ref.dataset)
        obj = get_indexed_object_meta(ref.dataset, ref.ref)
        sourced_id = f'{ref.ref}@{source.id}'

        bibitem, validation_errors = construct_bibitem(ref.body, strict)
        # NOTE: construct_bibitem() does loose YAML normalization
        # on ``ref.body`` IN-PLACE as a side-effect,
        # so we must call it first or CompositeSourcedBibliographicItem
        # may get bad YAML and fail validation.
        # XXX: Make normalization more explicit
        bibitem_merger.merge(base, ref.body)

        if validation_errors is not None:
            validation_errors_encountered = True

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

    if not strict and validation_errors_encountered:
        log.error(
            "Failed to validate composite sourced bibliographic item "
            "with primary docid %s "
            "(suppressed with strict=False)",
            primary_id)
        # We wouldn’t be able to initialize this instance normally
        # due to validation errors.
        return (
            CompositeSourcedBibliographicItem.construct(**composite),
            False,
        )
    else:
        # Either strict validation was requested,
        # or we didn’t encounter any validation errors above.
        # Validation errors at this stage would be considered bugs
        # in this codebase, and not an issue in source data.
        return (
            CompositeSourcedBibliographicItem(**composite),
            True,
        )


def get_docid_struct_for_search(id: DocID) -> Dict[str, Any]:
    """Converts a given ``DocID`` instance into a structure
    suitable for being passed
    to :func:`~main.query.search_refs_relaton_struct()`.
    """

    struct: Dict[str, Any] = {'id': id.id, 'type': id.type}
    if id.primary:
        struct['primary'] = True
    return struct


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
    see e.g. :func:`main.query.search_refs_relaton_field`.
    """

    err = repr(exc)
    return any((
        "invalid regular expression" in err,
        "syntax error" in err and "jsonpath input" in err,
        "unexpected end of quoted string" in err and "jsonpath input" in err,
    ))
