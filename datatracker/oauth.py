"""Authentication using Datatracker OIDC/OAuth2.
"""

from typing import List
import json
import logging

from pydantic import BaseModel, Extra
from requests_oauthlib import OAuth2Session
from simplejson import JSONDecodeError
import requests
from requests.exceptions import SSLError

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings

from .request import BASE_AUTH_DOMAIN


__all__ = (
    'get_client',
    'context_processor',
    'initiate',
    'handle_callback',
    'log_out',
    'clear_session',
    'get_provider',
    'ProviderInfo',
    'DEFAULT_PROVIDER',
)


log = logging.getLogger(__name__)


OAUTH_SCOPES = ['openid', 'profile']


# Redirection

get_default_post_oauth_redirect_url = lambda: reverse('browse')
"""
Where to redirect the user after:

- successful OAuth attempt,
  if nothing is available via :data:`~.OAUTH_INITIATED_FROM_URL_KEY`
  in session, or
- failed OAuth initiation,
  if “referer” is not available in request meta.
"""

# Credentials

CLIENT_ID = getattr(settings, 'DATATRACKER_CLIENT_ID', None) or None
"""Populated from :data:`~bibxml.settings.DATATRACKER_CLIENT_ID`."""

CLIENT_SECRET = getattr(settings, 'DATATRACKER_CLIENT_SECRET', None) or None
"""Populated from :data:`~bibxml.settings.DATATRACKER_CLIENT_SECRET`."""


# Session keys

OAUTH_STATE_KEY = 'oauth_state'
"""
Session key under which
the opaque state string used by OAuth implementation
is stored.
"""

OAUTH_TOKEN_KEY = 'oauth_token'
"""
Session key under which
the OAuth access token that can be used to make authenticated requests
is stored.
"""

OAUTH_USER_INFO_KEY = 'oauth_user_info'
"""
Session key under which
a dictionary with user data (username, etc.) obtained from OAuth2 provider
is stored.
"""

OAUTH_INITIATED_FROM_URL_KEY = 'oauth_initiated_from_url'
"""
Session key under which
the information on where the user was before they initiated OAuth flow
(to avoid the user losing their place after the redirect)
is stored.

.. note::

   Currently, contains a domain-relative path.
   This can theoretically cause a 404 if at the time of redirect
   URL configuration is no longer configured to handle
   the path stored in the session for some reason.
"""


def context_processor(request):
    """Adds context variables:

    - ``datatracker_oauth_enabled`` (boolean)
    - ``datatracker_user``, currently authenticated user info
    """
    try:
        _get_redirect_uri()
    except ImproperlyConfigured:
        ok = False
    else:
        ok = True if (CLIENT_ID and CLIENT_SECRET) else False

    ctx = dict(
        datatracker_oauth_enabled=ok,
    )

    if ok and OAUTH_USER_INFO_KEY in request.session:
        ctx['datatracker_user'] = request.session[OAUTH_USER_INFO_KEY]

    return ctx


def get_client(request):
    """Returns either an OAuth2Session, or None.

    Session is guaranteed to be authenticated,
    and can be used to perform authenticated operations.

    As a side effect, if session is not authenticated,
    clears OAuth data from session.
    """

    if OAUTH_TOKEN_KEY in request.session:
        session = OAuth2Session(
            CLIENT_ID,
            scope=OAUTH_SCOPES,
            redirect_uri=_get_redirect_uri(),
            token=request.session[OAUTH_TOKEN_KEY])
        provider = get_provider()
        try:
            session.get(provider.userinfo_endpoint).json()
        except Exception:
            # Most likely, token expired.
            clear_session(request)
            return None
        else:
            return session
    else:
        return None


def clear_session(request):
    """Removes Datatracker OAuth2 data from session."""

    keys = [
        OAUTH_TOKEN_KEY,
        OAUTH_STATE_KEY,
        OAUTH_USER_INFO_KEY,
        OAUTH_INITIATED_FROM_URL_KEY,
    ]
    for key in keys:
        try:
            del request.session[key]
        except KeyError:
            pass


def log_out(request):
    """Clears OAuth session and redirects to referer
    or :func:`~.get_default_post_oauth_redirect_url()`.
    """

    clear_session(request)
    return redirect(
        request.headers.get('referer', get_default_post_oauth_redirect_url())
    )


# Flow views
# ==========

def _get_redirect_uri() -> str:
    """Returns redirect URI without query string
    by reversing an URL pattern 'datatracker_oauth_callback'.

    :raises ImproperlyConfigured: obtained redirect URI
        does not match indicated in integration.
    """
    # We do not use Django’s request.build_absolute_uri here,
    # since origin may be accessed over plain HTTP.
    path = reverse('datatracker_oauth_callback')
    redirect_uri = f'https://{settings.HOSTNAME}{path}'

    if redirect_uri == settings.DATATRACKER_REDIRECT_URI:
        return redirect_uri
    else:
        log.error(
            "Datatracker OAuth: "
            "Calculated redirect URI %s "
            "does not match required %s",
            redirect_uri,
            settings.DATATRACKER_REDIRECT_URI)
        raise ImproperlyConfigured(
            f"Calculated redirect URI {redirect_uri} "
            f"does not match required {settings.DATATRACKER_REDIRECT_URI}")


def initiate(request):
    """A Django view that redirects the user to Datatracker
    for login and approval.

    If :data:`~datatracker.oauth.CLIENT_ID`
    or :data:`~datatracker.oauth.CLIENT_SECRET` are missing,
    or if obtained redirect URI does not match configuration,
    queues an error-level message and redirects the user back
    to where they came from or default post-OAuth redirect URL.
    """

    redirect_to = request.headers.get(
        'referer',
        get_default_post_oauth_redirect_url())
    # In case of error, user will be redirected here immediately.
    # Otherwise, will be stored in session to internally redirect the user
    # after OAuth callback.

    if not CLIENT_ID or not CLIENT_SECRET:
        log.warning(
            "Datatracker OAuth2: client ID/secret not configured, "
            "redirecting to home")
        messages.error(
            request,
            "Couldn’t authenticate with Datatracker: "
            "integration is not configured")
        return redirect(redirect_to)

    provider = get_provider()
    try:
        redirect_uri = _get_redirect_uri()
    except ImproperlyConfigured as err:
        messages.error(
            request,
            "Couldn’t authenticate with Datatracker: "
            "misconfigured redirect URI "
            f"({err})")
        return redirect(redirect_to)
    else:
        request.session[OAUTH_INITIATED_FROM_URL_KEY] = redirect_to
        session = OAuth2Session(
            CLIENT_ID,
            scope=OAUTH_SCOPES,
            redirect_uri=redirect_uri)
        auth_url, state = session.authorization_url(
            provider.authorization_endpoint)
        request.session[OAUTH_STATE_KEY] = state
        return redirect(auth_url, permanent=False)


def handle_callback(request):
    """
    A Django view that handles OAuth2 redirect from Datatracker’s side.

    Queues an error-level message if:

    - :data:`~datatracker.oauth.CLIENT_ID`
      or :data:`~datatracker.oauth.CLIENT_SECRET` are missing, or
    - obtained redirect URI does not match configuration, or
    - there is no OAuth state in session, or
    - there is any exception during token or user info retrieval,

    In any case, it redirects the user to HTTP Referer or landing page.
    """

    redirect_to = request.session.pop(
        OAUTH_INITIATED_FROM_URL_KEY,
        get_default_post_oauth_redirect_url())

    if not CLIENT_ID or not CLIENT_SECRET:
        log.warning(
            "Datatracker OAuth2 callback: client ID/secret not configured, "
            "redirecting to home")
        messages.error(
            request,
            "Couldn’t authenticate with Datatracker: "
            "integration is not configured")
        return redirect(redirect_to)

    if OAUTH_STATE_KEY not in request.session:
        log.warning(
            "Datatracker OAuth2 callback: no state in session, "
            "redirecting to home")
        messages.warning(
            request,
            "Couldn’t authenticate with Datatracker, "
            "please try again.")
        return redirect(redirect_to)

    try:
        redirect_uri = _get_redirect_uri()
    except ImproperlyConfigured as err:
        messages.error(
            request,
            "Couldn’t authenticate with Datatracker: "
            "misconfigured redirect URI "
            f"({err})")
        return redirect(redirect_to)

    provider = get_provider()

    try:
        session = OAuth2Session(
            CLIENT_ID,
            scope=OAUTH_SCOPES,
            redirect_uri=redirect_uri,
            state=request.session[OAUTH_STATE_KEY])
    except Exception as err:
        log.exception("Datatracker OAuth: failed to instantiate session")
        messages.error(
            request,
            f"Failed to instantiate OAuth2 session ({err})")
    else:
        auth_response = f'{redirect_uri}?{request.GET.urlencode()}'
        try:
            token = session.fetch_token(
                provider.token_endpoint,
                client_secret=CLIENT_SECRET,
                include_client_id=True,
                code=request.GET.get('code'),
                authorization_response=auth_response)
        except Exception as err:
            log.exception("Datatracker OAuth: failed to retrieve token")
            messages.error(
                request,
                f"Failed to fetch token ({err})")
        else:
            request.session[OAUTH_TOKEN_KEY] = token

            try:
                session_with_token = OAuth2Session(
                    CLIENT_ID,
                    scope=OAUTH_SCOPES,
                    state=request.session[OAUTH_STATE_KEY],
                    token=token)
                user_info = session_with_token.get(
                    provider.userinfo_endpoint).json()
            except Exception as err:
                log.exception("Datatracker OAuth: failed to get user info")
                clear_session(request)
                messages.error(
                    request,
                    f"Failed to fetch user info ({err})")
            else:
                request.session[OAUTH_USER_INFO_KEY] = user_info
                log.info("datatracker.oauth: Got user info: %s", json.dumps(user_info))
                messages.success(
                    request,
                    "You have authenticated via Datatracker")

    return redirect(redirect_to)


# Provider info
# =============

class ProviderInfo(BaseModel, extra=Extra.ignore):
    """Describes OAuth2 provider."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    end_session_endpoint: str
    introspection_endpoint: str
    response_types_supported: List[str]
    id_token_signing_alg_values_supported: List[str]
    subject_types_supported: List[str]
    token_endpoint_auth_methods_supported: List[str]


def get_provider() -> ProviderInfo:
    """Tries to obtain up-to-date OAuth2 provider info
    from IETF auth’s .well-known file,
    falls back to :data:`.DEFAULT_PROVIDER` if failed.
    """

    try:
        data = requests.get(
            f'{BASE_AUTH_DOMAIN}api/openid/.well-known/openid-configuration',
        ).json()
    except (JSONDecodeError, SSLError):
        log.warn(
            "Invalid response from Datatracker’s OAuth provider spec, "
            "falling back to hard-coded data")
        return DEFAULT_PROVIDER
    else:
        return ProviderInfo(**data)


DEFAULT_PROVIDER = ProviderInfo(**{
    "issuer": "https://auth.ietf.org/api/openid",
    "authorization_endpoint": "https://auth.ietf.org/api/openid/authorize",
    "token_endpoint": "https://auth.ietf.org/api/openid/token",
    "userinfo_endpoint": "https://auth.ietf.org/api/openid/userinfo",
    "end_session_endpoint": "https://auth.ietf.org/api/openid/end-session",
    "introspection_endpoint": "https://auth.ietf.org/api/openid/introspect",
    "response_types_supported": [
        "code",
        "id_token",
        "id_token token",
        "code token",
        "code id_token",
        "code id_token token",
    ],
    "jwks_uri": "https://auth.ietf.org/api/openid/jwks",
    "id_token_signing_alg_values_supported": [
        "HS256",
        "RS256",
    ],
    "subject_types_supported": [
        "public",
    ],
    "token_endpoint_auth_methods_supported": [
        "client_secret_post",
        "client_secret_basic",
    ],
})
"""Datatracker OAuth2 provider info
manually obtained from .well-known/openid-configuration."""
