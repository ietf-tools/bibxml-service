import traceback
from os import path

from celery.utils.log import get_task_logger

from .celery import app
from .repo import ensure_latest
from .datasets import locate_bibxml_source_repo, locate_relaton_source_repo
from .utils import get_work_dir_path
from .index import index_dataset
from .task_status import IndexingTaskCeleryMeta


logger = get_task_logger(__name__)


def _fetch_and_index(task, dataset_id, refs=None):
    """(Re)indexes given dataset.

    :param refs: a list of refs to index,
                 if not provided the entire dataset is indexed

    :returns:

        An object of the shape::

            { total: int,
              indexed: int,
              refs: comma-separated string of requested refs }
    """

    task_desc: IndexingTaskCeleryMeta = dict(
        action='starting indexing {}'.format(dataset_id),
        progress={'total': 3, 'current': 0},
        dataset_id=dataset_id,
        requested_refs=','.join(refs or []),
    )

    task.update_state(
        state='PROGRESS',
        meta=task_desc,
    )

    try:
        bibxml_repo_url, bibxml_repo_branch = \
            locate_bibxml_source_repo(dataset_id)
        bibxml_work_dir_path = get_work_dir_path(
            dataset_id,
            bibxml_repo_url,
            bibxml_repo_branch)

        task.update_state(
            state='PROGRESS',
            meta={
                **task_desc,
                'progress': {
                    'total': 3,
                    'current': 1,
                },
                'action':
                    'pulling or cloning BibXML source '
                    'from {} (branch {}) into {}'
                    .format(
                        bibxml_repo_url,
                        bibxml_repo_branch,
                        bibxml_work_dir_path),
            },
        )

        ensure_latest(
            bibxml_repo_url,
            bibxml_repo_branch,
            bibxml_work_dir_path)

        bibxml_data_dir = path.join(bibxml_work_dir_path, 'data')

        # TODO: #25 Use relaton-bib-py to generate Relaton data

        relaton_repo_url, relaton_repo_branch = \
            locate_relaton_source_repo(dataset_id)
        relaton_work_dir_path = get_work_dir_path(
            dataset_id,
            relaton_repo_url,
            relaton_repo_branch)

        task.update_state(
            state='PROGRESS',
            meta={
                **task_desc,
                'progress': {
                    'total': 3,
                    'current': 2
                },
                'action':
                    'pulling or cloning Relaton source '
                    'from {} (branch {}) into {}'
                    .format(
                        relaton_repo_url,
                        relaton_repo_branch,
                        relaton_work_dir_path),
            },
        )

        ensure_latest(
            relaton_repo_url,
            relaton_repo_branch,
            relaton_work_dir_path)

        relaton_data_dir = path.join(relaton_work_dir_path, 'data')

        update_status = (lambda total, indexed: task.update_state(
                state='PROGRESS',
                meta={
                    **task_desc,
                    'action':
                        'indexing using BibXML data in {} '
                        'and Relaton data in {}'
                        .format(
                            bibxml_data_dir,
                            relaton_data_dir),
                    'progress': {
                        'total': total,
                        'current': indexed,
                    },
                },
            )
        )

        total, indexed = index_dataset(
            dataset_id,
            bibxml_data_dir,
            relaton_data_dir,
            refs,
            update_status)

        return {
            **task_desc,
            'progress': {
                'total': total,
                'current': indexed,
            },
        }

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

fetch_and_index = app.task(bind=True)(_fetch_and_index)
