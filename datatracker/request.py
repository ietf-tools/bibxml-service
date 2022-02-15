import requests


BASE_DOMAIN = 'https://datatracker.ietf.org'


def post(endpoint: str, api_key: str) -> requests.Response:
    """Handles Datatracker authenticated POST request.
    """
    return requests.post(
        f'{BASE_DOMAIN}/{endpoint}',
        files={'apikey': (None, api_key)},
    )


def get(endpoint: str, format='json') -> requests.Response:
    """Handles Datatracker GET request, specifies JSON format.
    """
    return requests.get(
        f'{BASE_DOMAIN}/{endpoint}',
        params={'format': format} if format else None,
    )
