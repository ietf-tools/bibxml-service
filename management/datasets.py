from django.conf import settings
from main.types import IndexedSourceMeta


GITHUB_REPO_URL = "https://github.com/{user}/{repo}"


def get_source_meta(dataset_id: str) -> IndexedSourceMeta:
    internal_repo_name = f'relaton-data-{dataset_id}'
    internal_repo_github = \
        f'https://github.com/ietf-ribose/{internal_repo_name}'

    return IndexedSourceMeta(
        id=internal_repo_name,
        home_url=internal_repo_github,
        issues_url=f'{internal_repo_github}/issues',
    )


def locate_bibxml_source_repo(dataset_id):
    """
    :param dataset_id: dataset ID as string
    :returns: tuple (repo_url, repo_branch)
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


def locate_relaton_source_repo(dataset_id):
    """
    .. note:: Deprecated when ``relaton-bib-py`` generates Relaton data.

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
