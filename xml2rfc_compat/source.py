"""
Registers an indexable source representing paths
available via xml2rfc web server for fallback
during data migration.
"""

import glob
import os
from typing import List, Union, Callable, Tuple

from django.db import transaction

from sources import indexable

from .models import Xml2rfcItem


def index_xml2rfc_source(
    work_dirs: List[str],
    refs: Union[List[str], None],
    on_progress: Callable[[int, int], None],
    on_error: Callable[[str, str], None],
) -> Tuple[int, int]:
    """
    Indexes data from an xml2rfc web server mirror repository.

    Uses :class:`.models.Xml2rfcItem` to store indexed data.
    """

    on_progress = on_progress or (lambda total, indexed: None)

    if len(work_dirs) > 1:
        raise RuntimeError("Received too many working directories")

    if refs is not None:
        raise RuntimeError("This source does not support partial reindexing")

    work_dir = work_dirs[0]

    source_xml_files = glob.glob("%s/**/*.xml" % work_dir, recursive=True)

    total = len(source_xml_files)

    if total < 0:
        raise RuntimeError("Repository does not contain data")

    on_progress(total, 0)

    indexed_paths = set()

    with transaction.atomic():
        for idx, xml_fpath in enumerate(source_xml_files):
            on_progress(total, idx)

            with open(xml_fpath, 'r', encoding='utf-8') as xml_fhandler:
                try:
                    xml_data = xml_fhandler.read()
                except UnicodeDecodeError as err:
                    on_error(xml_fpath, str(err))
                    continue
                else:
                    if '\x00' in xml_data:
                        on_error(xml_fpath, "NUL character in XML string")
                        continue

            _pparts = xml_fpath.split(os.sep)
            dirname, fname = _pparts[-2], _pparts[-1]
            relative_fpath = f'{dirname}{os.sep}{fname}'
            Xml2rfcItem.objects.update_or_create(
                subpath=relative_fpath,
                xml_repr=xml_data)

            indexed_paths.add(relative_fpath)

        # Delete all preexisting files not found in source anymore
        Xml2rfcItem.objects.exclude(subpath__in=indexed_paths).delete()

    return total, len(indexed_paths)


indexable.register_git_source(
    'xml2rfc',
    [('https://github.com/ietf-ribose/bibxml-data-archive', 'main')],
)({
    'indexer': index_xml2rfc_source,
    'count_indexed': Xml2rfcItem.objects.count,
    'reset_index': (lambda: Xml2rfcItem.objects.all().delete()),
})
