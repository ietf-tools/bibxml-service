"""
Celery task for working with indexable sources.
"""
from typing import List, Tuple
import traceback
from textwrap import indent
from celery.utils.log import get_task_logger

from .celery import app

from .indexable import registry
from .task_status import IndexingTaskCeleryMeta, push_task
from .models import SourceIndexationOutcome


logger = get_task_logger(__name__)


def fetch_and_index_task(task, dataset_id: str, refs=None):
    """(Re)indexes indexable source with given ID.

    :param str dataset_id: source ID used during registration.
    :param refs: a list of items to index,
                 if not provided the entire dataset is indexed

    :rtype: sources.task_status.IndexingTaskCeleryMeta
    """

    try:
        indexable_source = registry[dataset_id]
    except KeyError:
        logger.exception(
            "Failed to index source %s: Source not registered",
            dataset_id)
        return

    push_task(dataset_id, task.request.id)

    task_desc = IndexingTaskCeleryMeta(
        action='starting indexing {}'.format(dataset_id),
        progress={'total': 0, 'current': 0},
        dataset_id=dataset_id,
        requested_refs=','.join(refs or []),
    )

    task.update_state(
        state='PROGRESS',
        meta=task_desc,
    )

    update_status = (lambda action, total, indexed: task.update_state(
        state='PROGRESS',
        meta={
            **task_desc,
            'action': action,
            'progress': {
                'total': total,
                'current': indexed,
            },
        },
    ))

    item_errors: List[Tuple[str, str]] = []

    on_error = (lambda item, err: item_errors.append((item, err)))

    outcome = SourceIndexationOutcome(
        source_id=dataset_id,
        task_id=task.request.id,
        notes=f"Requested for: {','.join(refs or []) or 'all'}\n",
    )

    def try_save_failed_outcome(err: str):
        try:
            outcome.notes += f"Failed with error:\n{err}"
            outcome.successful = False
            outcome.save()
        except Exception:
            pass

    try:
        found, indexed = indexable_source.index(refs, update_status, on_error)

    except SystemExit:
        logger.exception(
            "Failed to index dataset %s: Task aborted with SystemExit",
            dataset_id)
        traceback.print_exc()
        print("Indexing {}: Task aborted with SystemExit".format(dataset_id))
        try_save_failed_outcome("SystemExit")
        raise

    except Exception as err:
        logger.exception(
            "Failed to index dataset %s: Task failed",
            dataset_id)
        traceback.print_exc()
        print("Indexing {}: Task failed to complete".format(dataset_id))

        try_save_failed_outcome(f"{err}")

        raise

    else:
        outcome.successful = True
        outcome.notes += (
            f"Total: {found}\n"
            f"Indexed: {indexed}\n"
            f"Problem items: {len(item_errors)}\n"
        )
        if len(item_errors) > 0:
            errors = '\n'.join([
                f"{item}:\n{indent(err, '    ')}"
                for item, err in item_errors
            ]) or 'N/A'
            outcome.notes += f"Problem items:\n{errors}\n"

        outcome.save()

        return {
            **task_desc,
            'progress': {
                'total': found,
                'current': indexed,
            },
        }


fetch_and_index = app.task(bind=True)(fetch_and_index_task)
