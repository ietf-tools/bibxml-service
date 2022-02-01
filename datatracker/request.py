import requests


API_BASE = 'https://datatracker.ietf.org/api'


def post(endpoint: str, api_key: str) -> requests.Response:
    """Handles Datatracker authenticated POST request.
    """
    return requests.post(
        f'{API_BASE}/{endpoint}',
        files={'apikey': (None, api_key)},
    )


def get(endpoint: str, format='json') -> requests.Response:
    """Handles Datatracker GET request, specifies JSON format.
    """
    return requests.post(
        f'{API_BASE}/{endpoint}',
        params={'format': format} if format else None,
    )
