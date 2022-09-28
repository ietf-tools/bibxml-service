"""View functions for API endpoints."""

from django.http import JsonResponse

from celery.result import AsyncResult

from sources.tasks import fetch_and_index
from sources.celery import app
from sources.task_status import get_dataset_task_history, push_task
from sources import indexable


def run_indexer(request, dataset_name: str):
    """Starts indexing for given dataset."""

    force = request.GET.get('force', False)

    # TODO: Quickly check sources for given dataset before queueing indexing

    refs_raw = request.POST.get('refs', None)
    refs = refs_raw.split(',') if refs_raw else None

    result = fetch_and_index.delay(dataset_name, refs, force)
    task_id = result.id

    if task_id:
        push_task(dataset_name, task_id)

    return JsonResponse({
        "message": "Queued indexing for {} with task ID {}".format(
            dataset_name,
            task_id),
    })


def reset_index(request, dataset_name):
    """Clears index for dataset."""

    try:
        source = indexable.registry[dataset_name]
    except KeyError:
        return JsonResponse({
            "error": {
                "message": "Index for {} had been reset".format(dataset_name),
            }
        })
    else:
        source.reset_index()
        return JsonResponse({
            "message": "Index for {} had been reset".format(dataset_name),
        })


def indexer_status(request, dataset_name):
    """Retrieves information about latest indexing tasks for dataset."""

    return JsonResponse({
        "tasks": get_dataset_task_history(dataset_name),
    })


def stop_task(request, task_id):
    """Revokes and attempts to terminate a task given its ID."""

    task = AsyncResult(task_id, app=app)
    task.revoke(terminate=True)

    return JsonResponse({
        "message": "Task {} has been revoked".format(task_id),
    })


def stop_all_tasks(request):
    """Revokes any pending tasks, does not guarantee termination."""

    app.control.purge()

    try:
        # TODO: Check that forced task termination works with stop-all
        jobs = app.control.inspect().active()
        for hostname in jobs:
            tasks = jobs[hostname]
            for task in tasks:
                task = AsyncResult(task['id'], app=app)
                task.revoke(terminate=True)
    except:  # noqa: E722
        return JsonResponse({
            "message": "Pending tasks were revoked, active tasks may remain",
        })
    else:
        return JsonResponse({
            "message": "Pending tasks were revoked",
        })
