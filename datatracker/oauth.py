"""Authentication using Datatracker OIDC/OAuth2.
"""

from typing import List
import logging

from pydantic import BaseModel, Extra
from requests_oauthlib import OAuth2Session
from simplejson import JSONDecodeError
from requests.exceptions import SSLError

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings

from . import request


log = logging.getLogger(__name__)

OAUTH_STATE_KEY = 'oauth_state'
OAUTH_TOKEN_KEY = 'oauth_token'
OAUTH_USER_INFO_KEY = 'oauth_user_info'

CLIENT_ID = getattr(settings, 'DATATRACKER_CLIENT_ID', None)
CLIENT_SECRET = getattr(settings, 'DATATRACKER_CLIENT_SECRET', None)


def context_processor(request):
    """Adds context variables:

    - ``datatracker_oauth_enabled`` (boolean)
    - ``datatracker_user``, currently authenticated user info
    """
    ctx = dict(
        datatracker_oauth_enabled=CLIENT_ID and CLIENT_SECRET,
    )

    if OAUTH_USER_INFO_KEY in request:
        return dict(
            datatracker_user=request[OAUTH_USER_INFO_KEY],
            **ctx,
        )
    else:
        return ctx


def log_out(request):
    """Removes Datatracker user info from session."""
    try:
        del request.session[OAUTH_USER_INFO_KEY]
    except KeyError:
        pass
    return redirect('/')


# Flow views
# ==========

def _get_redirect_uri() -> str:
    """Returns redirect URI without query string.

    :raises ImproperlyConfigured: mismatching redirect URI in integration.
    """
    # We do not use Django’s request.build_absolute_uri here,
    # since origin may be accessed over plain HTTP.
    path = reverse('datatracker_oauth_callback')
    redirect_uri = f'https://{settings.HOSTNAME}{path}'

    if redirect_uri == settings.DATATRACKER_REDIRECT_URI:
        return redirect_uri
    else:
        log.exception(
            "Datatracker OAuth: "
            "Calculated redirect URI %s "
            "does not match required %s",
            redirect_uri,
            settings.DATATRACKER_REDIRECT_URI)
        raise ImproperlyConfigured(
            f"Calculated redirect URI {redirect_uri} "
            f"does not match required {settings.DATATRACKER_REDIRECT_URI}")


def initiate(request):
    if not CLIENT_ID or not CLIENT_SECRET:
        log.warning(
            "Datatracker OAuth2: client ID/secret not configured, "
            "redirecting to home")
        messages.error(
            request,
            "Couldn’t authenticate with Datatracker: "
            "integration is not configured")
        return redirect('/')

    provider = get_provider_info()
    try:
        redirect_uri = _get_redirect_uri()
    except ImproperlyConfigured as err:
        messages.error(
            request,
            "Couldn’t authenticate with Datatracker: "
            "misconfigured redirect URI "
            f"({err})")
        return redirect('/')
    else:
        session = OAuth2Session(CLIENT_ID, scope=['openid'], redirect_uri=redirect_uri)
        auth_url, state = session.authorization_url(
            provider.authorization_endpoint)
        request.session[OAUTH_STATE_KEY] = state
        return redirect(auth_url, permanent=False)


def handle_callback(request):
    if not CLIENT_ID or not CLIENT_SECRET:
        log.warning(
            "Datatracker OAuth2 callback: client ID/secret not configured, "
            "redirecting to home")
        messages.error(
            request,
            "Couldn’t authenticate with Datatracker: "
            "integration is not configured")
        return redirect('/')

    if OAUTH_STATE_KEY not in request.session:
        log.warning(
            "Datatracker OAuth2 callback: no state in session, "
            "redirecting to home")
        messages.warning(
            request,
            "Couldn’t authenticate with Datatracker, "
            "please try again.")
        return redirect('/')

    provider = get_provider_info()

    try:
        session = OAuth2Session(
            CLIENT_ID,
            scope=['openid'],
            state=request.session[OAUTH_STATE_KEY])
    except Exception as err:
        log.exception("Datatracker OAuth: failed to instantiate session")
        messages.error(
            request,
            f"Failed to instantiate OAuth2 session ({err})")
    else:
        try:
            redirect_uri = _get_redirect_uri()
        except ImproperlyConfigured as err:
            messages.error(
                request,
                "Couldn’t authenticate with Datatracker: "
                "misconfigured redirect URI "
                f"({err})")
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
                        state=request.session[OAUTH_STATE_KEY],
                        token=token)
                    user_info = session_with_token.get(
                        provider.userinfo_endpoint).json()
                except Exception as err:
                    log.exception("Datatracker OAuth: failed to retrieve user info")
                    messages.error(
                        request,
                        f"Failed to fetch user info ({err})")
                else:
                    request.session[OAUTH_USER_INFO_KEY] = user_info
                    messages.success(
                        request,
                        "You have authenticated via Datatracker")

    return redirect('/')


# Provider info
# =============

class ProviderInfo(BaseModel, extra=Extra.ignore):
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


def get_provider_info():
    try:
        data = request.get(
            'openid/.well-known/openid-configuration',
            format=None,
        ).json()
    except (JSONDecodeError, SSLError):
        log.exception(
            "Invalid response from Datatracker’s OAuth provider spec, "
            "falling back to hard-coded data")
        data = {
            "issuer": "https://datatracker.ietf.org/api/openid",
            "authorization_endpoint": "https://datatracker.ietf.org/api/openid/authorize",
            "token_endpoint": "https://datatracker.ietf.org/api/openid/token",
            "userinfo_endpoint": "https://datatracker.ietf.org/api/openid/userinfo",
            "end_session_endpoint": "https://datatracker.ietf.org/api/openid/end-session",
            "introspection_endpoint": "https://datatracker.ietf.org/api/openid/introspect",
            "response_types_supported": [
              "code",
              "id_token",
              "id_token token",
              "code token",
              "code id_token",
              "code id_token token"
            ],
            "jwks_uri": "https://datatracker.ietf.org/api/openid/jwks",
            "id_token_signing_alg_values_supported": [
              "HS256",
              "RS256"
            ],
            "subject_types_supported": [
              "public"
            ],
            "token_endpoint_auth_methods_supported": [
              "client_secret_post",
              "client_secret_basic"
            ],
        }
    return ProviderInfo(**data)
