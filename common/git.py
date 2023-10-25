"""Utilities for dealing with Git."""

from typing import Tuple
from os import access, path, R_OK, W_OK, X_OK
from pathlib import Path
from shutil import rmtree
from git import Repo
from celery.utils.log import get_task_logger
from django.core.exceptions import SuspiciousOperation
from django.conf import settings


logger = get_task_logger(__name__)


def reclone(repo_url: str, branch: str, work_dir: str) \
        -> Repo:
    """
    Wipes proposed ``work_dir``
    and clones given repository into that location.
    Sets depth of 1 to avoid fetching history.
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

    Path(work_dir).mkdir(parents=True, exist_ok=True)

    repo = Repo.clone_from(repo_url, work_dir, branch=branch, depth=1)

    # Set name and email; may be required when pulling
    repo.config_writer().set_value("user", "name", "ci").release()
    repo.config_writer().set_value("user", "email", "ci@local").release()

    return repo


def ensure_latest(repo_url: str, branch: str, work_dir: str) \
        -> Tuple[Repo, bool]:
    """
    If specified working directory contains a Git repo
    matching provided configuration (URL and branch), performs a pull
    (fetch with depth of 1 and reset).

    Otherwise, removes working directory if it exists
    and clones the repository afresh.

    :returns: a tuple with GitPython’s Repo instance
              and a flag indicating whether head commit changed
              (always True if reclone was required).
    :rtype: (Repo, bool)
    """

    is_dir = path.isdir(work_dir)
    is_git_dir = path.isdir(path.join(work_dir, '.git'))
    is_accessible = access(work_dir, R_OK | W_OK | X_OK)

    if all([is_dir, is_git_dir, is_accessible]):
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
            "Missing or inaccessible working directory for %s (%s: %s), "
            "must re-clone repo",
            repo_url,
            work_dir,
            f'dir: {is_dir}, git: {is_git_dir}, access: {is_accessible}')
        return reclone(repo_url, branch, work_dir), True
