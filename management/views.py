"""View functions for management GUI."""

from django.shortcuts import render
from django.conf import settings
from django.http.request import split_domain_port

from .task_status import get_dataset_task_history, describe_indexing_task
from .task_status import list_running_tasks


shared_context = dict(
    # NOTE: Use this context only in auth-guarded views
    api_secret=settings.API_SECRET,
    known_datasets=settings.KNOWN_DATASETS,
    indexed_datasets=[
        ds
        for ds in settings.KNOWN_DATASETS
        if ds not in settings.EXTERNAL_DATASETS],
    authoritative_datasets=settings.AUTHORITATIVE_DATASETS,
    snapshot=settings.SNAPSHOT,
)


def manage(request):
    running_tasks = [
        describe_indexing_task(tid)
        for tid in list_running_tasks()]

    return render(request, 'management/home.html', dict(
        **shared_context,
        running_tasks=running_tasks,
        task_monitor_host="{}:{}".format(
            split_domain_port(request.get_host())[0],
            5555),
    ))


def manage_dataset(request, dataset_id):
    return render(request, 'management/dataset.html', dict(
        **shared_context,
        dataset_id=dataset_id,
        history=get_dataset_task_history(dataset_id),
    ))
