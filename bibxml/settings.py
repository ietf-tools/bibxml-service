from typing import List, Dict, Callable
from pathlib import Path
import re
from os import environ, path
import socket


BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(environ.get("DEBUG", default=0)) == 1

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'django.security.DisallowedHost': {
        'handlers': ['null'],
        'propagate': False,
    },
}


# Service info (custom)
# =====================

SNAPSHOT = environ.get("SNAPSHOT")
"""Actual version of this service codebase at runtime."""

SERVICE_NAME = environ.get("SERVICE_NAME")
"""Service title (short phrase)."""

HOSTNAME = environ.get("PRIMARY_HOSTNAME")
"""Primary hostname the service is publicly deployed under."""


# Networking/infrastructure
# =========================

detected_hostname, _, detected_ipv4_ips = socket.gethostbyname_ex(
    socket.gethostname())

if DEBUG:
    # Set internal IPs in Docker environment, per Django debug toolbar docs:
    INTERNAL_IPS = [
        ip[:-1] + '1'
        for ip in detected_ipv4_ips
    ] + ['127.0.0.1', '10.0.2.2']

INTERNAL_HOSTNAMES = [
    h.strip()
    for h in environ.get("INTERNAL_HOSTNAMES", "").split(',')
    if h.strip() != ''
]

if environ.get("RESPOND_TO_DETECTED_INTERNAL_HOSTNAME", 0) == 1:
    INTERNAL_HOSTNAMES.append(detected_hostname)

if environ.get("RESPOND_TO_DETECTED_INTERNAL_IPS", 0) == 1:
    INTERNAL_HOSTNAMES.extend(detected_ipv4_ips)

ALLOWED_HOSTS = [
    HOSTNAME,
    *INTERNAL_HOSTNAMES,
]


# Basic Django settings
# =====================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environ.get("DJANGO_SECRET")

ADMINS = [(
    "%s operations" % environ.get("SERVICE_NAME"),
    environ.get("CONTACT_EMAIL"),
)]


if environ.get("SENTRY_DSN", None):
    import sentry_sdk
    import logging
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=environ.get("SENTRY_DSN"),
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.WARNING,
            ),
        ],
        server_name=HOSTNAME,
        # Can be adjusted in production to reduce overhead.
        traces_sample_rate=1.0,
        send_default_pii=False,
    )


INSTALLED_APPS = [
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'main.app.Config',
    'management.app.Config',
    'xml2rfc_compat.app.Config',
    'compressor',
    'debug_toolbar',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'common.query_profiler.middleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

ROOT_URLCONF = 'bibxml.urls'

APPEND_SLASH = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'common.query_profiler.context_processor',
                'bibxml.context_processors.service_meta',
                'bibxml.context_processors.sources',
                'bibxml.context_processors.matomo',
                'datatracker.oauth.context_processor',
                'sources.indexable.context_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'bibxml.wsgi.application'

CSRF_USE_SESSIONS = True

if DEBUG:
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000']
    SESSION_COOKIE_DOMAIN = 'localhost'
else:
    CSRF_TRUSTED_ORIGINS = [f'https://{HOSTNAME}']
    SESSION_COOKIE_DOMAIN = HOSTNAME


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': environ.get('DB_NAME'),
        'USER': environ.get('DB_USER'),
        'PASSWORD': environ.get('DB_SECRET'),
        'HOST': environ.get('DB_HOST'),
        'PORT': int(environ.get('DB_PORT') or 5432),
    }
}


# NOTE: This project isn’t intended to be used with conventional Django auth,
# hence this setting is empty.
AUTH_PASSWORD_VALIDATORS: List[str] = []


# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Email

EMAIL_SUBJECT_PREFIX = f"[Django at {HOSTNAME}] "

if environ.get("SERVER_EMAIL", None):
    SERVER_EMAIL = environ.get("SERVER_EMAIL")


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

STATICFILES_DIRS = [
    BASE_DIR / 'static'
]
STATIC_ROOT = BASE_DIR / 'build' / 'static'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)


# Django compressor

BABEL_CONFIG = BASE_DIR / 'babel.config.json'
"""Absolute path to Babel configuration file for front-end build."""

BABEL_EXECUTABLE = 'npx babel'
"""How to invoke Babel."""

POSTCSS_EXECUTABLE = 'npx postcss'
"""How to invoke PostCSS CLI."""

COMPRESS_PRECOMPILERS = (
   # ('text/jsx', 'cat {infile} | babel --config-file %s > {outfile}' % BABEL_CONFIG),
   (
       'text/javascript',
       '%s {infile} --config-file %s --source-maps --out-file {outfile}'
       % (BABEL_EXECUTABLE, BABEL_CONFIG),
   ),
   (
       'text/css',
       '%s {infile} -o {outfile}'
       % (POSTCSS_EXECUTABLE, ),
   ),
)

COMPRESS_ENABLED = True
COMPRESS_OFFLINE = not DEBUG

if DEBUG:
    COMPRESS_MTIME_DELAY = 2


# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Celery

CELERY_BROKER_URL = environ.get('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = environ.get('CELERY_RESULT_BACKEND')

CELERY_SEND_TASK_SENT_EVENT = True
CELERY_WORKER_SEND_TASK_EVENTS = True

# TODO: Figure out correct identifier scope for the TRACK_STARTED Celery setting
CELERY_TASK_TRACK_STARTED = True
CELERY_TRACK_STARTED = True

CELERY_WORKER_CONCURRENCY = 1
CELERY_TASK_RESULT_EXPIRES = 604800


# Redis

REDIS_HOST = environ.get('REDIS_HOST')
REDIS_PORT = environ.get('REDIS_PORT', 0)


# Caching

if environ.get('REDIS_HOST') and environ.get('REDIS_PORT'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}',
        }
    }


# Matomo

MATOMO = {
    'url': environ.get("MATOMO_URL", None),
    'site_id': environ.get("MATOMO_SITE_ID", None),
    'tm_container': environ.get("MATOMO_TAG_MANAGER_CONTAINER", None),
}
"""
Setting ``url`` and either ``site_id`` or ``tm_container``
activates Matomo integration.

- ``site_id`` is used for basic tracking integration.
- If ``tm_container`` is set,
  tag manager is used and ``site_id`` has no effect.

  To integrate tag manager, set container
  to the <CONTAINER> part of the “https://.../js/container_<CONTAINER>.js”
  string, which you will find within the tag manager snippet obtained
  from your Matomo dashboard.

.. seealso:: :func:`bibxml.context_processors.matomo`
"""


# Datatracker

DATATRACKER_CLIENT_ID = environ.get("DATATRACKER_CLIENT_ID", '').strip()
"""Datatracker client ID for OAuth2 integration."""

DATATRACKER_CLIENT_SECRET = environ.get("DATATRACKER_CLIENT_SECRET", '').strip()
"""Datatracker client secret for OAuth2 integration."""

DATATRACKER_REDIRECT_URI = environ.get(
    "DATATRACKER_REDIRECT_URI",
    f"https://{HOSTNAME or '(hostname at runtime)'}/datatracker-auth/callback/")
"""Redirect URI configured on Datatracker side."""


# Custom

DEFAULT_CACHE_SECONDS = 21600
"""How long to cache by default."""

SEARCH_CACHE_SECONDS = 3600
"""How long to cache search results for."""


# BibXML-specific
# ===============

DEFAULT_SEARCH_RESULT_LIMIT = 400
"""Default hard limit for found item count.

If the user hits this limit, they are expected to provide
a more precise query."""

DATASET_TMP_ROOT = environ.get('DATASET_TMP_ROOT', '/data/datasets')
"""Where to keep fetched source data and data generated during indexing.
Should be a directory. No trailing slash."""


# API access
# ----------

API_USER = 'ietf'
"""Username for HTTP Basic auth to access management GUI."""

API_SECRETS = [
    environ.get('API_SECRET'),
    *[
        s.strip()
        for s in environ.get('EXTRA_API_SECRETS', '').split(',')
        if s.strip() != ''
    ],
]
"""Secrets used to authenticate API requests and access to management GUI.
Obtained from environment variables ``API_SECRET`` and ``EXTRA_API_SECRETS``.

.. seealso:: :doc:`/topics/auth`
"""


# Relaton dataset sources
# -----------------------

RELATON_DATASETS = [
    'rfcs',
    'ids',
    'rfcsubseries',
    'misc',
    'w3c',
    '3gpp',
    'ieee',
    'iana',
    'nist',
]
"""A list of Relaton source IDs.
Must refer to existing Git repositories
(see :func:`main.sources.locate_relaton_source_repo` for a remark on that).

Settings following below define how the service obtains Git repository
URL and branch corresponding to those datasets at indexing stage.
"""

DEFAULT_DATASET_REPO_URL_TEMPLATE = "https://github.com/ietf-ribose/relaton-data-{dataset_id}"
"""Used to obtain default Git repository URL for a Relaton source,
if override is not specified in :data:`.DATASET_SOURCE_OVERRIDES`.

Intended to be used with ``.format()``
and must accept placeholder ``dataset_id``.

.. seealso:: :mod:`main.sources`
"""

DEFAULT_DATASET_REPO_BRANCH = 'main'
"""Default Git repository branch name for Relaton source repository,
if override is not specified in :data:`.DATASET_SOURCE_OVERRIDES`.

.. seealso:: :mod:`main.sources`
"""

DATASET_SOURCE_OVERRIDES = {
    'ieee': {
        'relaton_data': {
            'repo_url': 'https://github.com/ietf-ribose/relaton-data-ieee',
        },
    },
}
"""Overrides Relaton source location (Git repository URL and branch).
Supports partial overrides.

For any dataset ID from :data:`.RELATON_DATASETS` that is *not* listed here,
:data:`.DEFAULT_DATASET_REPO_URL_TEMPLATE`
and :data:`.DEFAULT_DATASET_REPO_BRANCH` are used as fallbacks.

.. seealso:: :mod:`main.sources`
"""


# xml2rfc compatibility
# ---------------------

XML2RFC_COMPAT_DIR_ALIASES = {
    'bibxml': ['bibxml-rfcs'],
    'bibxml2': ['bibxml-misc'],
    'bibxml3': ['bibxml-ids'],
    'bibxml4': ['bibxml-w3c'],
    'bibxml5': ['bibxml-3gpp'],
    'bibxml6': ['bibxml-ieee'],
    'bibxml7': ['bibxml-doi'],
    'bibxml8': ['bibxml-iana'],
    'bibxml9': ['bibxml-rfcsubseries'],
}
"""Maps dirname to a list of aliases to reflect
IETF xml2rfc web server behavior.
"""

XML2RFC_PATH_PREFIX = 'public/rfc/'
"""Global prefix relative to which all xml2rfc-style paths are treated.
This prefix is subtracted from further resolution.

Must have trailing slash, but no leading slash.
"""


# Other
# -----

AUTHORITATIVE_DATASETS = [
    'rfcs',
    'ids',
    'rfcsubseries',
]
"""A list of authoritative datasets.
"""
