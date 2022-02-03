"""Utilities for dealing with Git."""

from typing import Tuple
from os import access, path, R_OK
from shutil import rmtree
from git import Repo  # type: ignore[attr-defined]
from celery.utils.log import get_task_logger
from django.core.exceptions import SuspiciousOperation
from django.conf import settings


logger = get_task_logger(__name__)


def reclone(repo_url: str, branch: str, work_dir: str) \
        -> Repo:
    """
    Wipes proposed ``work_dir``,
    and clones given repository into that location.
    """

    if path.commonpath([
        settings.DATASET_TMP_ROOT,
        path.realpath(work_dir),
    ]) != settings.DATASET_TMP_ROOT:
        raise SuspiciousOperation(
            "Cannot reclone to a dir outside DATASET_TMP_ROOT")

    try:
        rmtree(work_dir)
    except FileNotFoundError:
        pass

    repo = Repo.clone_from(repo_url, work_dir, branch=branch)

    # Set name and email; may be required when pulling
    repo.config_writer().set_value("user", "name", "ci").release()
    repo.config_writer().set_value("user", "email", "ci@local").release()

    return repo


def ensure_latest(repo_url: str, branch: str, work_dir: str) \
        -> Tuple[Repo, bool]:
    """
    If specified working directory contains a Git repo
    matching provided configuration (URL and branch), performs a pull.

    Otherwise, removes working directory if it exists
    and clones the repository afresh.

    :returns: a tuple with GitPython’s Repo instance
              and a flag indicating whether head commit changed
              (always True if reclone was required).
    :rtype: (Repo, bool)
    """

    if all([path.isdir(work_dir),
            path.isdir(path.join(work_dir, '.git')),
            access(work_dir, R_OK)]):

        repo = Repo(work_dir)

        if all(['origin' in repo.remotes,
                repo.remotes.origin.exists(),
                repo.remotes.origin.url == repo_url,
                repo.active_branch.name == branch]):
            try:
                sha_before_pull = repo.head.commit.hexsha
                repo.remotes.origin.fetch(branch, depth=1, update_shallow=True)
                repo.head.reset(
                    'origin/{}'.format(branch),
                    hard=True,
                    working_tree=True)
            except:  # noqa: E722
                logger.exception("Failed to fetch or check out branch")
                raise
            else:
                return repo, repo.head.commit.hexsha != sha_before_pull
        else:
            logger.warning(
                "Invalid repo config in working directory for %s (%s), "
                "must re-clone repo",
                repo_url, work_dir)
            return reclone(repo_url, branch, work_dir), True
    else:
        logger.warning(
            "Missing or inaccessible working directory for %s (%s), "
            "must re-clone repo",
            repo_url, work_dir)
        return reclone(repo_url, branch, work_dir), True
