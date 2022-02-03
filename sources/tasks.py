"""
Celery task for working with indexable sources.
"""
import traceback
from celery.utils.log import get_task_logger

from .celery import app

from .indexable import registry
from .task_status import IndexingTaskCeleryMeta


logger = get_task_logger(__name__)


def _fetch_and_index(task, dataset_id: str, refs=None):
    """(Re)indexes given indexable source.

    :param str dataset_id: source ID used during registration.
    :param refs: a list of items to index,
                 if not provided the entire dataset is indexed

    :rtype: IndexingTaskCeleryMeta
    """

    try:
        indexable_source = registry[dataset_id]
    except KeyError:
        logger.exception(
            "Failed to index source %s: Source not registered",
            dataset_id)
        return

    task_desc: IndexingTaskCeleryMeta = dict(
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

    try:
        found, indexed = indexable_source.index(refs, update_status, None)

    except SystemExit:
        logger.exception(
            "Failed to index dataset %s: Task aborted with SystemExit",
            dataset_id)
        traceback.print_exc()
        print("Indexing {}: Task aborted with SystemExit".format(dataset_id))
        raise

    except:  # noqa: E722
        logger.exception(
            "Failed to index dataset %s: Task failed",
            dataset_id)
        traceback.print_exc()
        print("Indexing {}: Task failed to complete".format(dataset_id))
        raise

    else:
        return {
            **task_desc,
            'progress': {
                'total': found,
                'current': indexed,
            },
        }


fetch_and_index = app.task(bind=True)(_fetch_and_index)
