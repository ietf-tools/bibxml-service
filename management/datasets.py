from django.conf import settings
from main.types import IndexedSourceMeta, IndexedObject


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
