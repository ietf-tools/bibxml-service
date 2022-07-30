"""Primitives for working with indexing task status."""

from typing import List, Optional, TypedDict, Union, cast
import time
import datetime
import traceback

from celery.result import AsyncResult

from .celery import app
from .models import SourceIndexationOutcome
from . import cache


TaskError = TypedDict(
    'TaskError',
    {'type': str, 'message': str})
"""Error description for a failed task."""


TaskProgress = TypedDict(
    'TaskProgress',
    {'total': Union[int, None], 'current': int})
"""Progress description for task in progress."""


class IndexingTaskCeleryMeta(TypedDict):
    """
    Represents extra metadata for indexing task.
    This structure is stored in Celery using the ``meta`` attribute.
    """

    requested_refs: Optional[str]  # Union[list[str], None]
    """Citation refs requested for indexing, as a comma-separated list."""

    dataset_id: str
    """Dataset ID being indexed."""

    action: str
    """Description of currently performed action, for a task in progress."""

    progress: TaskProgress
    """Indexation progress status."""


class IndexingTaskDescription(TypedDict):
    """
    Indexing task description is built from Celery’s basic task metadata
    and custom metadata that conforms to :class:`IndexingTaskCeleryMeta`.
    """

    task_id: str
    """Celery task ID."""

    status: str
    """Upper-case string describing Celery task state."""

    requested_refs: Union[List[str], None]
    """Citation refs requested for indexing."""

    dataset_id: Union[str, None]
    """Dataset ID being indexed."""

    outcome_summary: Union[str, None]
    """Outcome description, normally for a successful task."""

    completed_at: Optional[datetime.datetime]
    """Completion timestamp as a string, normally for a successful task."""

    action: Union[str, None]
    """Description of currently performed action, for a task in progress."""

    progress: Union[TaskProgress, None]
    """Indexation progress status."""

    error: Union[TaskError, None]
    """Error description, for a failed task."""


def get_task_ids(dataset_id, limit=10) -> List[str]:
    """Retrieves Celery task IDs for dataset indexing runs,
    ordered from most recently started to least recently started.

    :param dataset_id: dataset ID
    :param limit: how many task IDs to return, by default 10 most recent
    :returns: list of task IDs as strings"""

    return cache.lrange(dataset_id, 0, limit)


def push_task(dataset_id, task_id):
    """Adds given ``task_id`` to the top of the list for given dataset,
    and sets a key with task metadata (currently, requested refs).

    Removes any instances of ``task_id`` recorded for this dataset beforehand,
    so can be run multiple times.

    :param task_id: Celery task ID.
    """

    cache.lrem(dataset_id, 0, task_id)
    cache.lpush(dataset_id, task_id)


def _sort_by_task_timestamp(task: IndexingTaskDescription) -> float:
    if date := task.get('completed_at', None):
        return time.mktime(date.timetuple())
    elif task.get('progress', None):
        return time.mktime(datetime.datetime.now().timetuple())
    else:
        return 0


def get_dataset_task_history(dataset_name, limit=10) -> \
        List[IndexingTaskDescription]:

    task_ids = list(dict.fromkeys([
        *get_task_ids(dataset_name, limit),
        *SourceIndexationOutcome.objects.
        filter(source_id=dataset_name).
        order_by('-timestamp').
        values_list('task_id', flat=True),
    ]))

    return sorted([
        describe_indexing_task(tid)
        for tid in task_ids
    ], key=_sort_by_task_timestamp, reverse=True)


def get_latest_outcome(dataset_name: str) -> Optional[IndexingTaskDescription]:
    try:
        latest_task_id = get_task_ids(dataset_name, limit=1)[0]
    except IndexError:
        latest_outcome = (
            SourceIndexationOutcome.objects.
            filter(source_id=dataset_name).
            order_by('-timestamp').
            first())
        if latest_outcome:
            latest_task_id = latest_outcome.task_id
        else:
            return None

    return describe_indexing_task(latest_task_id)


def list_running_tasks() -> List[str]:
    jobs = app.control.inspect().active()
    return [
        task['id']
        for hostname in (jobs or [])
        for task in jobs.get(hostname, [])]


def describe_indexing_task(tid: str) -> IndexingTaskDescription:
    """Using Celery task ID, collects indexing task description.

    If Celery task referenced by the ID does not represent an indexing task
    and lacks relevant metadata, outcome will be nonsensical.
    """

    result = AsyncResult(tid, app=app)
    task: IndexingTaskDescription = dict(
        task_id=tid,
        status=result.status,

        completed_at=None,
        dataset_id=None,
        requested_refs=None,
        action=None,
        progress=None,
        error=None,
        outcome_summary=None,
    )

    try:
        outcome = SourceIndexationOutcome.objects.get(task_id=tid)
    except SourceIndexationOutcome.DoesNotExist:
        outcome = None

    # Try outcome record stored in DB
    if outcome:
        task['dataset_id'] = outcome.source_id
        task['completed_at'] = outcome.timestamp
        if outcome.successful:
            task['status'] = 'SUCCESS'
            task['outcome_summary'] = outcome.notes
        else:
            task['status'] = 'FAILURE'
            task['error'] = outcome.notes

    # Otherwise, try task state in Celery backend
    else:
        meta = cast(IndexingTaskCeleryMeta, result.info or {})

        if isinstance(meta, Exception):
            task['error'] = dict(
                type=getattr(meta.__class__, '__name__', 'N/A'),
                message='\n'.join(traceback.format_exception(
                    meta.__class__,
                    meta,
                    meta.__traceback__)))
        else:
            refs = meta.get('requested_refs', None)
            task['requested_refs'] = refs.split(',') if refs else None

            task['dataset_id'] = meta.get('dataset_id', 'N/A')

            prog = meta.get('progress', {})
            total, current = \
                prog.get('total', None), prog.get('current', None)

            if result.successful():
                task['outcome_summary'] = \
                    "Succeeded (total: {}, indexed: {})".format(
                        total if total is not None else 'N/A',
                        current if current is not None else 'N/A')
                if result.date_done:
                    task['completed_at'] = result.date_done

            elif result.failed():
                err_msg = meta.get('exc_message', ['N/A'])
                task['error'] = dict(
                    type=str(meta.get('exc_type', 'N/A')),
                    message='\n'.join(err_msg)
                            if isinstance(err_msg, list)
                            else repr(err_msg))

            else:
                task['action'] = meta.get('action', 'N/A')
                if current is not None:
                    progress: TaskProgress = dict(
                        current=current,
                        total=None)
                    if total is not None:
                        progress['total'] = total
                    task['progress'] = progress

    return task
