import hashlib
from os import path, makedirs

from django.conf import settings


def get_dataset_tmp_path(dataset_id):
    """
    :returns string: Path to dataset data root under ``DATASET_TMP_ROOT``.
    """
    ds_path = path.join(settings.DATASET_TMP_ROOT, dataset_id)

    if not path.exists(ds_path):
        makedirs(ds_path)
    elif not path.isdir(ds_path):
        raise RuntimeError("Dataset path exists, but isn’t a directory")

    return ds_path


def get_work_dir_path(dataset_id, repo_url, repo_branch):
    """Returns a unique working directory path based on given parameters,
    under ``DATASET_TMP_ROOT`` setting."""

    dir = hashlib.sha224(
        "{}::{}".
        format(repo_url, repo_branch).
        encode('utf-8')).hexdigest()

    return path.join(get_dataset_tmp_path(dataset_id), dir)
