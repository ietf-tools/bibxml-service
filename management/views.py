"""View functions for management GUI."""

from typing import List, Optional
from dataclasses import dataclass

from django.shortcuts import render
from django.conf import settings
from django.http.request import split_domain_port
from django.utils.timesince import timesince

from sources.task_status import get_dataset_task_history
from sources.task_status import describe_indexing_task
from sources.task_status import list_running_tasks
from sources.task_status import get_latest_outcome, TaskProgress
from sources import indexable


shared_context = dict(
    # NOTE: Use this context only in auth-guarded views
    api_secret=settings.API_SECRETS[0],
)


def home(request):
    running_tasks = [
        describe_indexing_task(tid)
        for tid in list_running_tasks()
    ]

    return render(request, 'management/home.html', dict(
        **shared_context,
        running_tasks=running_tasks,
        task_monitor_host="{}:{}".format(
            split_domain_port(request.get_host())[0],
            5555),
    ))


@dataclass
class IndexableSourceStatus:
    name: str
    status: str
    item_count: str
    task_id: Optional[str]
    task_progress: Optional[TaskProgress]


def datasets(request):
    """Indexable sources."""

    sources: List[IndexableSourceStatus] = []
    for source_id, source in indexable.registry.items():
        task = get_latest_outcome(source_id)

        status: str
        if task is None:
            status = "status unknown"
        elif task['progress']:
            status = f"in progress ({task['action'] or 'N/A'})"
        elif task['completed_at']:
            try:
                ago = timesince(task['completed_at'], depth=1)
            except Exception:
                ago = ''
            status = (
                f"last indexed {ago} ago "
                f"({task['completed_at'].strftime('%Y-%m-%dT%H:%M:%SZ')})")
        else:
            status = "status unknown"
        # TODO: Annotate/aggregate indexed item counts in management GUI?
        sources.append(IndexableSourceStatus(
            name=source_id,
            status=status,
            task_id=task['task_id'] if task else None,
            task_progress=task['progress']
            if task and 'progress' in task
            else None,
            item_count=str(source.count_indexed()),
        ))

    return render(request, 'management/datasets.html', dict(
        **shared_context,
        datasets=sources,
    ))


def dataset(request, dataset_id: str):
    """:term:`indexable source` indexing history & running tasks."""

    return render(request, 'management/dataset.html', dict(
        **shared_context,
        dataset_id=dataset_id,
        history=get_dataset_task_history(dataset_id),
    ))


def indexing_task(request, task_id: str):
    """Indexing task run for an indexable source."""

    return render(request, 'management/task.html', dict(
        **shared_context,
        dataset_id=request.GET.get('dataset_id', None),
        task=describe_indexing_task(task_id),
    ))
