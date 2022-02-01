import requests


API_BASE = 'https://datatracker.ietf.org/api'


def post(endpoint: str, api_key: str) -> requests.Response:
    """Handles Datatracker POST request and unpacks JSON from response.

    :raises simplejson.JSONDecodeError:
        if JSON could not be unpacked.

    :raises json.JSONDecodeError:
        if JSON could not be unpacked and simplejson is not installed.
    """
    return requests.post(
        f'{API_BASE}/{endpoint}',
        files={'apikey': (None, api_key)},
    )


def get(endpoint: str, format='json') -> requests.Response:
    """Handles Datatracker GET request, specifies JSON format
    and unpacks JSON from response.

    :raises simplejson.JSONDecodeError:
        if JSON could not be unpacked.

    :raises json.JSONDecodeError:
        if JSON could not be unpacked and simplejson is not installed.
    """
    return requests.post(
        f'{API_BASE}/{endpoint}',
        params={'format': format} if format else None,
    )
