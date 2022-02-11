"""
Facilities for registering and listing available indexable sources.

See :term:`indexable source`.
"""
import functools
import hashlib
from dataclasses import dataclass
from typing import Callable, Union, List, Tuple, Dict, TypedDict
from os import path, makedirs

from celery.utils.log import get_task_logger
from django.conf import settings

from common.git import ensure_latest

from . import cache


log = get_task_logger(__name__)
"""Celery task logger.
Log events are expected only when ran in Celery context.
"""


@dataclass
class IndexableSource:
    """
    Represents an indexable source.

    An instance of this class will be automatically created
    when you use the :func:`register_git_source` decorator.
    """

    index: Callable[
        [
            Union[List[str], None],
            Union[Callable[[str, int, int], None], None],
            Union[Callable[[str, str], None], None],
        ],
        Tuple[int, int],
    ]
    """
    The indexer function. Takes 3 positional arguments,
    any of which can be None:

    1) a list of source-specific references to index
       (absence means “index all”)
    2) an on-progress handler
       (which should be called with an action as a string
       and 2 ints, total and indexed).
    3) an on-error handler, called with 2 strings
       (problematic item and error description).

    Returns 2-tuple of integers
    (number of found items, number of indexed items).
    """

    count_indexed: Callable[[], int]
    """A function that returns the number of indexed items for this source."""

    reset_index: Callable[[], None]
    """A function that wipes all indexed data for this source.
    Takes no arguments and returns nothing."""


registry: Dict[str, IndexableSource] = {}
"""
Registry of indexable sources.

Each indexable source is represented by a function
that handles data retrieval and indexing.
"""


class IndexableSourceToRegister(TypedDict, total=True):
    """A dictionary expected by indexable source registration."""

    indexer: Callable[
        [
            List[str],
            Union[List[str], None],
            Callable[[int, int], None],
            Callable[[str, str], None],
        ],
        Tuple[int, int]
    ]
    """
    A function that will receive 4 positional arguments:

    1) a list of directories pre-filled with repository contents
       (one for each of repository sources specified during registration),
    2) a list of references to index (or None),
    3) an on-progress handler that should be called
       with 2 ints (total and indexed) on each indexed item,
    4) an on-error handler that should be called
       with 2 strings (problematic item name and error description).

    It must return a 2-tuple (number of found items, number of indexed items).

    It should raise an exception if the source had not been indexed
    due to a problem.
    """

    count_indexed: Callable[[], int]
    """A function that returns the number of indexed items for this source."""

    reset_index: Callable[[], None]
    """A function that wipes all indexed data for this source.
    Takes no arguments and returns nothing."""


def register_git_source(source_id: str, repos: List[Tuple[str, str]]):
    """
    Parametrized decorator that returns a registration function
    for an indexable source that uses one or more Git repositories.

    Each repository is configured by a 2-tuple of strings
    (Git HTTPS URL, Git branch).

    The indexable source being registered should be a dictionary conforming
    to :class:`IndexableSourceToRegister`.

    Returned wrapper will handle things like fetching Git repositories
    and checking that head commits changed before calling registered
    indexer implementation.
    """

    latest_indexed_heads_key = f'{source_id}_latest_indexed_heads'

    def wrapper(index_info: IndexableSourceToRegister):
        total_repos = len(repos)

        if source_id in registry:
            log.warning(
                "Attempt to register source with same ID: %s",
                source_id)
            return

        def default_on_progress(action: str, total: int, indexed: int):
            log.info(
                "Indexing %s (no progress handler): %s (%s of %s)",
                source_id,
                action,
                indexed,
                total)

        def default_on_item_error(item: str, err: str):
            log.warning(
                "Error indexing item %s in %s (and no error handler): %s",
                item,
                source_id,
                err)

        @functools.wraps(index_info['indexer'])
        def handle_index(
            refs: Union[List[str], None],
            on_progress: Union[Callable[[str, int, int], None], None],
            on_item_error: Union[Callable[[str, str], None], None],
        ) -> Tuple[int, int]:
            work_dir_paths: List[str] = []
            repo_heads: List[str] = []

            on_progress = on_progress or default_on_progress
            on_item_error = on_item_error or default_on_item_error

            for idx, (repo_url, repo_branch) in enumerate(repos):
                work_dir_path = get_work_dir_path(
                    source_id,
                    repo_url,
                    repo_branch)
                work_dir_paths.append(work_dir_path)

                on_progress(
                    'pulling or cloning '
                    'from {} (branch {}) into {}'
                    .format(
                        repo_url,
                        repo_branch,
                        work_dir_path),
                    total_repos,
                    idx + 1,
                )

                repo, _ = ensure_latest(
                    repo_url,
                    repo_branch,
                    work_dir_path)

                repo_heads.append(repo.head.commit.hexsha)

            heads_serialized = ', '.join(repo_heads)

            if cache.get(latest_indexed_heads_key) != heads_serialized:
                log.info(
                    "Repositories changed for %s, starting index",
                    source_id)
                on_index_progress = (lambda total, indexed: on_progress(
                    'indexing using data in {}'
                    .format(', '.join(repo[0] for repo in repos)),
                    total,
                    indexed,
                ))
                found, indexed = index_info['indexer'](
                    work_dir_paths,
                    refs,
                    on_index_progress,
                    on_item_error,
                )

                # If next indexing run encounters same heads combo, skip index.
                # Only set this key after index run completed without errors.
                cache.set(latest_indexed_heads_key, heads_serialized)

                return found, indexed

            else:
                log.info(
                    "No repositories changed for %s, skipping indexing",
                    source_id)
                return 0, 0

        indexable_source = IndexableSource(
            index=handle_index,
            reset_index=index_info['reset_index'],
            count_indexed=index_info['count_indexed'],
        )

        registry[source_id] = indexable_source

    return wrapper


def _get_dataset_tmp_path(source_id: str):
    """
    :returns string: Path to fetched source data root
                     under :data:`bibxml.settings.DATASET_TMP_ROOT`.
    """
    ds_path = path.join(settings.DATASET_TMP_ROOT, source_id)

    if not path.exists(ds_path):
        makedirs(ds_path)
    elif not path.isdir(ds_path):
        raise RuntimeError(
            "Source work directory path is occupied, "
            "and isn’t a directory")

    return ds_path


def get_work_dir_path(source_id: str, repo_url, repo_branch):
    """Returns a unique working directory path based on given parameters,
    under :data:`bibxml.settings.DATASET_TMP_ROOT`."""

    dir = hashlib.sha224(
        "{}::{}".
        format(repo_url, repo_branch).
        encode('utf-8')).hexdigest()

    return path.join(_get_dataset_tmp_path(source_id), dir)


def context_processor(request):
    """Makes ``indexable_sources`` available to templates."""

    return dict(
        indexable_sources=registry.keys(),
    )
