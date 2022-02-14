"""
Implements indexing logic
and registers :term:`indexable sources <indexable source>`
of bibliographic data
based on the list in :data:`bibxml.settings.RELATON_DATASETS`
using :func:`sources.indexable.register_git_source()`.

Each of the repositories is expected to follow certain structure
with Relaton bibliographic item data serialized to YAML files
under ``/data/`` directory under repository root
(see :func:`.index_dataset()` for indexing logic).

.. seealso:: :rfp:req:`3`
"""
import glob
from os import path
from typing import Tuple

import yaml
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction

from sources import indexable
from sources.types import IndexedSourceMeta, IndexedObject

from .models import RefData


logger = get_task_logger(__name__)


# Repository discovery
# ===================

GITHUB_REPO_URL = "https://github.com/{user}/{repo}"


get_github_web_data_root = (
    lambda repo_home, branch:
    f'{repo_home}/tree/{branch}'
)
get_github_web_issues = (
    lambda repo_home:
    f'{repo_home}/issues'
)


def get_source_meta(dataset_id: str) -> IndexedSourceMeta:
    """Should be used on ``dataset_id``
    that represents an ietf-ribose relaton-data-* repo."""

    repo_home, _ = locate_relaton_source_repo(dataset_id)
    repo_name = repo_home.split('/')[-1]
    repo_issues = get_github_web_issues(repo_home)

    return IndexedSourceMeta(
        id=repo_name,
        home_url=repo_home,
        issues_url=repo_issues,
    )


def get_indexed_object_meta(dataset_id: str, ref: str) -> IndexedObject:
    repo_home, branch = locate_relaton_source_repo(dataset_id)
    file_url = f'{get_github_web_data_root(repo_home, branch)}/data/{ref}.yaml'
    return IndexedObject(
        name=ref,
        external_url=file_url,
    )


def locate_bibxml_source_repo(dataset_id: str):
    """
    .. deprecated:: Service now generates bibxml on the fly,
                    and bibxml source repos will be excluded.

    :param dataset_id: dataset ID as string
    :returns: 2-tuple of strings (repo_url, repo_branch)
    """
    overrides = (getattr(settings, 'DATASET_SOURCE_OVERRIDES', {}).
                 get(dataset_id, {}).
                 get('bibxml_data', {}))
    return (
        overrides.get(
            'repo_url',
            GITHUB_REPO_URL.format(
                user='ietf-ribose',
                repo='bibxml-data-%s' % dataset_id)),
        overrides.get('repo_branch', 'main'),
    )


def locate_relaton_source_repo(dataset_id: str):
    """
    :param dataset_id: dataset ID as string
    :returns: tuple (repo_url, repo_branch)
    """
    overrides = (getattr(settings, 'DATASET_SOURCE_OVERRIDES', {}).
                 get(dataset_id, {}).
                 get('relaton_data', {}))

    return (
        overrides.get(
            'repo_url',
            GITHUB_REPO_URL.format(
                user='ietf-ribose',
                repo='relaton-data-%s' % dataset_id)),
        overrides.get('repo_branch', 'main'),
    )


# Source registration
# ===================


def register_relaton_source(source_id: str):
    indexable.register_git_source(
        source_id,
        [
            locate_relaton_source_repo(source_id),
            locate_bibxml_source_repo(source_id),
        ],
    )({
        'indexer': (lambda dirs, refs, on_progress, on_error: index_dataset(
            source_id,
            path.join(dirs[1], 'data'),
            path.join(dirs[0], 'data'),
            refs,
            on_progress,
            on_error,
        )),
        'reset_index': (lambda: reset_index_for_dataset(source_id)),
        'count_indexed': (
            lambda: RefData.objects.filter(dataset=source_id).count()
        ),
    })


for source_id in settings.RELATON_DATASETS:
    register_relaton_source(source_id)


# Indexing implementation
# =======================

yaml.SafeLoader.yaml_implicit_resolvers = {
    k: [r for r in v if r[0] != "tag:yaml.org,2002:timestamp"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def index_dataset(ds_id, bibxml_path, relaton_path, refs=None,
                  on_progress=None, on_error=None) -> Tuple[int, int]:
    """Indexes Relaton data into :class:`~.models.RefData` instances.

    :param ds_id: dataset ID as a string
    :param bibxml_path: path to BibXML source files
    :param relaton_path: path to Relaton source files

    :param refs: a list of string refs to index, or nothing to index everything
    :param on_progress: progress report lambda taking two ints (total, indexed)

    :returns: a tuple of two integers (total, indexed)

    :raise EnvironmentError: passes through any IOError, FileNotFoundError etc.
    """

    report_progress = on_progress or (lambda total, current: print(
        "Indexing {}: {} of {}".format(ds_id, total, current))
    )

    requested_refs = set(refs or [])
    indexed_refs = set()

    bibxml_source_files = glob.glob("%s/*.xml" % bibxml_path)

    total = len(bibxml_source_files)

    if total < 1:
        raise RuntimeError("The source is empty")

    report_progress(total, 0)

    with transaction.atomic():
        for idx, bibxml_fpath in enumerate(bibxml_source_files):
            ref = path.splitext(path.basename(bibxml_fpath))[0]

            if refs is None or ref in requested_refs:
                report_progress(total, idx)

                with open(bibxml_fpath, 'r', encoding='utf-8') \
                     as bibxml_fhandler:
                    bibxml_data = bibxml_fhandler.read()

                    relaton_fpath = path.join(relaton_path, '%s.yaml' % ref)

                    if path.exists(relaton_fpath):
                        with open(relaton_fpath, 'r', encoding='utf-8') \
                             as relaton_fhandler:
                            ref_data = yaml.load(
                                relaton_fhandler.read(),
                                Loader=yaml.SafeLoader)

                            RefData.objects.update_or_create(
                                ref=ref,
                                dataset=ds_id,
                                defaults=dict(
                                    body=ref_data,
                                    representations=dict(bibxml=bibxml_data)
                                ),
                            )

                            indexed_refs.add(ref)
                    else:
                        on_error(bibxml_fpath, "Failed to read Relaton source")
                        logger.warn(
                            "Failed to read Relaton source for %s",
                            bibxml_fpath)

        if refs is not None:
            # If we’re indexing a subset of refs,
            # and some of those refs were not found in source,
            # delete those refs from the dataset.
            missing_refs = requested_refs - indexed_refs
            (RefData.objects.
                filter(dataset=ds_id).
                exclude(ref__in=missing_refs).
                delete())

        else:
            # If we’re reindexing the entire dataset,
            # delete all refs not found in source.
            (RefData.objects.
                filter(dataset=ds_id).
                exclude(ref__in=indexed_refs).
                delete())

    return total, len(indexed_refs)


def reset_index_for_dataset(ds_id):
    """Deletes all references for given dataset."""

    with transaction.atomic():
        (RefData.objects.
            filter(dataset=ds_id).
            delete())
