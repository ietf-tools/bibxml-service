"""A Redis cache is used to keep track of Celery task IDs and dataset IDs
they operate on.

This means if Redis is down, we may lose this correspondence,
but Celery-provided admin UI can still be used to monitor status of tasks
(just without dataset correspondence)."""

from typing import List, Optional, TypedDict, Union
import traceback

from celery.result import AsyncResult

from .celery import app
from . import cache


TaskError = TypedDict(
    'TaskError',
    {'type': str, 'message': str})

TaskProgress = TypedDict(
    'TaskProgress',
    {'total': Union[int, None], 'current': int})


class IndexingTaskCeleryMeta(TypedDict):
    requested_refs: Optional[str]  # Union[list[str], None]
    """Citation refs requested for indexing, as a comma-separated list."""

    dataset_id: str
    """Dataset ID being indexed."""

    action: str
    """Description of currently performed action, for a task in progress."""

    progress: TaskProgress
    """Indexation progress status."""


class IndexingTaskDescription(TypedDict):
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

    completed_at: Union[str, None]
    """Completion timestamp as a string, normally for a successful task."""

    action: Union[str, None]
    """Description of currently performed action, for a task in progress."""

    progress: Union[TaskProgress, None]
    """Indexation progress status."""

    error: Union[TaskError, None]
    """Error description, for a failed task."""


def get_task_ids(dataset_id, limit=10):
    """Retrieves Celery task IDs for dataset indexing runs,
    ordered from most recently started to least recently started.

    :param dataset_id: dataset ID
    :param limit: how many task IDs to return, by default 10 most recent
    :returns: list of task IDs as strings"""

    return cache.lrange(dataset_id, 0, limit)


def push_task(dataset_id, task_id):
    """Adds given ``task_id`` to the top of the list for given dataset,
    and sets a key with task metadata (currently, requested refs).

    :param task_id: Celery task ID."""

    cache.lpush(dataset_id, task_id)


def get_dataset_task_history(dataset_name, limit=10) -> \
        List[IndexingTaskDescription]:
    task_ids = get_task_ids(dataset_name, limit)
    tasks = []

    for tid in task_ids:
        tasks.append(describe_indexing_task(tid))

    return tasks


def list_running_tasks() -> List[str]:
    jobs = app.control.inspect().active()
    return [task['id'] for hostname in jobs for task in jobs[hostname]]


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

    meta = result.info or {}

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
                task['completed_at'] = \
                    result.date_done.strftime('%Y-%m-%dT%H:%M:%SZ')

        elif result.failed():
            err_msg = meta.get('exc_message', ['N/A'])
            task['error'] = dict(
                type=meta.get('exc_type', 'N/A'),
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
