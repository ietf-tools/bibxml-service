"""Authentication uses token provided via API_SECRET Django setting,
provisioned at deploy time.
"""

import functools
import base64

from django.http.response import HttpResponse, HttpResponseForbidden
from django.conf import settings


def api(viewfunc):
    """Header token auth. Use for management API endpoints."""
    @functools.wraps(viewfunc)
    def wrapper(request, *args, **kwargs):
        provided_secret = request.headers.get('x-ietf-token', None)
        if provided_secret is not None:
            if provided_secret in settings.API_SECRETS:
                return viewfunc(request, *args, **kwargs)
        return HttpResponseForbidden("Not authorized.")

    return wrapper


def basic(viewfunc):
    """HTTP Basic auth. Use for management HTML views."""
    @functools.wraps(viewfunc)
    def wrapper(request, *args, **kwargs):
        auth = request.headers.get('authorization', '').split()
        if len(auth) == 2 and auth[0].lower() == 'basic':
            auth_raw = bytes(auth[1], 'utf-8')
            auth = base64.b64decode(auth_raw).decode('utf-8')
            user, password = auth.split(':')
            if user == settings.API_USER and password in settings.API_SECRETS:
                return viewfunc(request, *args, **kwargs)

        response = HttpResponse()
        response.status_code = 401
        response['WWW-Authenticate'] = 'Basic realm="bibxml-management"'
        return response

    return wrapper
