"""Utilities for dealing with Git."""

from os import access, path, rmdir, R_OK
from celery.utils.log import get_task_logger
from git import Repo  # type: ignore[attr-defined]


logger = get_task_logger(__name__)


def reclone(repo_url, branch, work_dir):
    try:
        rmdir(work_dir)
    except FileNotFoundError:
        pass

    repo = Repo.clone_from(repo_url, work_dir, branch=branch)

    # Set name and email; may be required when pulling
    repo.config_writer().set_value("user", "name", "ci").release()
    repo.config_writer().set_value("user", "email", "ci@local").release()

    return repo


def ensure_latest(repo_url, branch, work_dir):
    """If specified working directory contains a Git repo
    matching provided configuration (URL and branch), performs a pull.

    Otherwise, removes working directory if it exists
    and clones the repository afresh.

    :returns: Repo instance"""

    if all([path.isdir(work_dir),
            path.isdir(path.join(work_dir, '.git')),
            access(work_dir, R_OK)]):

        repo = Repo(work_dir)

        if all(['origin' in repo.remotes,
                repo.remotes.origin.exists(),
                repo.remotes.origin.url == repo_url,
                repo.active_branch.name == branch]):
            try:
                repo.remotes.origin.fetch(branch, depth=1, update_shallow=True)
                repo.head.reset(
                    'origin/{}'.format(branch),
                    hard=True,
                    working_tree=True)
            except:  # noqa: E722
                logger.exception("Failed to fetch or check out branch")
                raise

        else:
            repo = reclone(repo_url, branch, work_dir)

    else:
        repo = reclone(repo_url, branch, work_dir)

    return repo
