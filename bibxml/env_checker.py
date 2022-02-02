from typing import List, Tuple, Callable, Any
from os import environ

from django.core import checks
from django.conf import settings


def env_checker(**kwargs):
    """Checks that environment contains requisite variables."""

    env_checks: List[Tuple[
        str,
        Callable[[Any], bool],
        str
    ]] = [(
        'CONTACT_EMAIL',
        lambda val: val.strip() != '',
        "contact email must be specified",
    ), (
        'SERVICE_NAME',
        lambda val: val.strip() != '',
        "service name must be specified",
    ), (
        'PRIMARY_HOSTNAME',
        lambda val: all([
            val.strip() != '',
            val.strip() != '*' or settings.DEBUG,
        ]),
        "primary hostname must be specified",
    ), (
        'DB_NAME',
        lambda val: val.strip() != '',
        "default PostgreSQL database name must be specified",
    ), (
        'DB_USER',
        lambda val: val.strip() != '',
        "database username must be specified",
    ), (
        'DB_SECRET',
        lambda val: val.strip() != '',
        "database user credential must be specified",
    ), (
        'DB_HOST',
        lambda val: val.strip() != '',
        "default database server hostname must be specified",
    ), (
        'DB_PORT',
        lambda val: val.strip() != '',
        "default database server port number must be specified",
    ), (
        'DJANGO_SECRET',
        lambda val: val.strip() != '',
        "Django secret must be set",
    ), (
        'REDIS_HOST',
        lambda val: val.strip() != '',
        "Redis server host must be specified",
    ), (
        'REDIS_PORT',
        lambda val: val.strip() != '',
        "Redis server port must be specified",
    ), (
        'SNAPSHOT',
        lambda val: val.strip() != '',
        "snapshot must be specified (use git describe --abbrev=0)",
    )]

    failed_env_checks: List[Tuple[str, str]] = [
        (name, err)
        for name, check, err in env_checks
        if check(str(environ.get(name, ''))) is False
    ]

    return [
        checks.Error(
            f'{failed_check[1]}',
            hint=f'(variable {failed_check[0]}',
        )
        for failed_check in failed_env_checks
    ]
