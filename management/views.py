"""View functions for management GUI."""

from typing import List, Union, Optional
from dataclasses import dataclass

from django.shortcuts import render
from django.conf import settings
from django.http.request import split_domain_port

from main.models import RefData

from sources.task_status import get_dataset_task_history
from sources.task_status import describe_indexing_task
from sources.task_status import list_running_tasks
from sources.task_status import IndexingTaskDescription, TaskProgress
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
    task_progress: Optional[TaskProgress]


def datasets(request):
    """Indexable sources."""

    sources: List[IndexableSourceStatus] = []
    for source_id, source in indexable.registry.items():
        task: Union[IndexingTaskDescription, None]
        try:
            task = get_dataset_task_history(source_id, limit=1)[0]
        except IndexError:
            task = None

        status: str
        if task is None:
            status = "no task history"
        elif task['progress']:
            status = f"in progress ({task['action'] or 'N/A'})"
        elif task['completed_at']:
            status = f"last indexed {task['completed_at']}"
        else:
            status = "task status expired"
        # TODO: Annotate/aggregate indexed item counts in management GUI?
        sources.append(IndexableSourceStatus(
            name=source_id,
            status=status,
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
    """Indexable source indexing history & running tasks."""

    return render(request, 'management/dataset.html', dict(
        **shared_context,
        dataset_id=dataset_id,
        history=get_dataset_task_history(dataset_id),
    ))
