import requests


BASE_DOMAIN = 'https://datatracker.ietf.org'
"""Base domain for Datatracker API."""


def post(endpoint: str, api_key: str) -> requests.Response:
    """Handles Datatracker authenticated POST request.

    :param str endpoint: Endpoint URL relative to :data:`.BASE_DOMAIN`,
        with leading slash.
    """
    return requests.post(
        f'{BASE_DOMAIN}{endpoint}',
        files={'apikey': (None, api_key)},
    )


def get(endpoint: str, format='json') -> requests.Response:
    """Handles Datatracker GET request, specifies JSON format.

    :param str endpoint: Endpoint URL relative to :data:`.BASE_DOMAIN`,
        with leading slash.
    """
    return requests.get(
        f'{BASE_DOMAIN}{endpoint}',
        params={'format': format} if format else None,
    )
