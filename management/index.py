"""Responsible for actually indexing fetched data for search."""

from os import path
import glob
import yaml

from celery.utils.log import get_task_logger
from django.db import transaction

# NOTE: Cross-app import is inelegant
from main.indexed import RefDataManager


logger = get_task_logger(__name__)


yaml.SafeLoader.yaml_implicit_resolvers = {
    k: [r for r in v if r[0] != "tag:yaml.org,2002:timestamp"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


class CannotReadSource(RuntimeError):
    """
    Sources for given items (``refs`` in ``dataset_id``)
    cannot be found or read.
    """

    def __init__(self, message, dataset_id, refs):
        super().__init__(message)
        self.dataset_id = dataset_id
        self.refs = refs


def index_dataset(ds_id, bibxml_path, relaton_path, refs=None,
                  on_progress=None):
    """Indexes dataset.

    :param ds_id: dataset ID as a string
    :param bibxml_path: path to BibXML source files
    :param relaton_path: path to Relaton source files

    :param refs: a list of string refs to index, or nothing to index everything
    :param on_progress: progress report lambda taking two ints (total, indexed)

    :returns: a tuple of two integers (total, indexed)

    :raise CannotReadSource: some requested refs were not found during indexing
    :raise EnvironmentError: passes through any IOError, FileNotFoundError etc.
    """

    report_progress = on_progress or (lambda total, current: print(
        "Indexing {}: {} of {}".format(ds_id, total, current))
    )

    requested_refs = set(refs or [])
    indexed_refs = set()

    bibxml_source_files = glob.glob("%s/*.xml" % bibxml_path)

    total = len(bibxml_source_files)

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

                            RefDataManager.update_or_create(
                                ref=ref,
                                dataset=ds_id,
                                defaults=dict(
                                    body=ref_data,
                                    representations=dict(bibxml=bibxml_data)
                                ),
                            )

                            indexed_refs.add(ref)
                    else:
                        logger.warn(
                            "Failed to read Relaton source for %s",
                            bibxml_fpath)

        if refs is not None:
            # If we’re indexing a subset of refs,
            # and some of those refs were not found in source,
            # delete those refs from the dataset.
            missing_refs = requested_refs - indexed_refs
            (RefDataManager.
                filter(dataset=ds_id).
                exclude(ref__in=missing_refs).
                delete())

        else:
            # If we’re reindexing the entire dataset,
            # delete all refs not found in source.
            (RefDataManager.
                filter(dataset=ds_id).
                exclude(ref__in=indexed_refs).
                delete())

    return total, len(indexed_refs)


def reset_index_for_dataset(ds_id):
    """Deletes all references for given dataset."""

    with transaction.atomic():
        (RefDataManager.
            filter(dataset=ds_id).
            delete())
