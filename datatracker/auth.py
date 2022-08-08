"""Authentication using Datatracker bibxml API developer tokens.
"""

import logging
import functools
from simplejson import JSONDecodeError

from django.http.response import HttpResponseForbidden
from django.conf import settings

from .request import post
from .oauth import get_client
from .exceptions import UnexpectedDatatrackerResponse


log = logging.getLogger(__name__)


def api(viewfunc):
    """Header-based auth decorator for Django views.
    Use for API endpoints that require Datatracker authentication.

    - Expects token under ``X-Datatracker-Token`` HTTP header.

    - If token is not provided,
      but current session contains a valid Datatracker token,
      it counts as well.

    :data:`bibxml.settings.REQUIRE_DATATRACKER_AUTH`
    makes this decorator no-op.
    """
    if not getattr(settings, 'REQUIRE_DATATRACKER_AUTH', False):
        return viewfunc

    @functools.wraps(viewfunc)
    def wrapper(request, *args, **kwargs):
        provided_secret = request.headers.get('x-datatracker-token', None)

        if provided_secret is not None:
            try:
                authenticated = token_is_valid(provided_secret)
            except UnexpectedDatatrackerResponse:
                log.exception(
                    "Datatracker returned something unexpected "
                    "while checking auth. token")
                return HttpResponseForbidden(
                    "Unable to verify Datatracker token")
            else:
                if authenticated:
                    return viewfunc(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden("Invalid Datatracker API key")

        elif get_client(request) is not None:
            return viewfunc(request, *args, **kwargs)

        return HttpResponseForbidden(
            "Missing Datatracker API key, or outdated OAuth2 access token")

    return wrapper


def token_is_valid(api_key: str) -> bool:
    """Returns True if API key is considered valid
    for bibxml endpoint by Datatracker.
    """
    resp = post('/api/appauth/bibxml', api_key)

    if resp.status_code == 200:
        try:
            data = resp.json()

        except JSONDecodeError as err:
            raise UnexpectedDatatrackerResponse(
                "Invalid JSON received (%s)"
                % err)

        else:
            success = data.get('success', None)
            if success not in [True, False]:
                raise UnexpectedDatatrackerResponse(
                    "Unexpected JSON structure (has %s)"
                    % ', '.join(data.keys() or ['no keys']))
            return data['success']

    elif resp.status_code == 403:
        # Datatracker seems to not return {success: false},
        # but to fail with 403
        return False

    else:
        raise UnexpectedDatatrackerResponse(
            "Unsuccessful request: %s %s (%s)"
            % (resp.status_code, resp.reason, resp.text))
