from typing import List, Dict, Callable
from pathlib import Path
import re
from os import environ, path


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
}

# Basic Django settings
# =====================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environ.get("DJANGO_SECRET")

ADMINS = [(
    "%s operations" % environ.get("SERVICE_NAME"),
    environ.get("CONTACT_EMAIL"),
)]

if DEBUG:
    import socket
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[:-1] + '1' for ip in ips] + ['127.0.0.1', '10.0.2.2']

INTERNAL_HOSTNAMES = [
    h.strip()
    for h in environ.get("INTERNAL_HOSTNAMES", "").split(',')
    if h.strip() != ''
]

ALLOWED_HOSTS = [
    environ.get("PRIMARY_HOSTNAME"),
    *INTERNAL_HOSTNAMES,
]


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
        server_name=environ.get("PRIMARY_HOSTNAME"),
        # Can be adjusted in production to reduce overhead.
        traces_sample_rate=1.0,
        send_default_pii=False,
    )


INSTALLED_APPS = [
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main.app.Config',
    'management.app.Config',
    'compressor',
    'debug_toolbar',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'bibxml.wsgi.application'


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

EMAIL_SUBJECT_PREFIX = f"[Django at {environ.get('PRIMARY_HOSTNAME', '')}] "

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

# TODO: Figure out correct identifier scope for the TRACK_STARTED Celery setting
CELERY_TASK_TRACK_STARTED = True
CELERY_TRACK_STARTED = True

CELERY_WORKER_CONCURRENCY = 1
CELERY_TASK_RESULT_EXPIRES = 604800


# Redis

REDIS_HOST = environ.get('REDIS_HOST')
REDIS_PORT = environ.get('REDIS_PORT', 0)


# Caching

DEFAULT_CACHE_SECONDS = 21600
SEARCH_CACHE_SECONDS = 3600

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
"""


# Datatracker

DATATRACKER_CLIENT_ID = environ.get("DATATRACKER_CLIENT_ID", '')
DATATRACKER_CLIENT_SECRET = environ.get("DATATRACKER_CLIENT_SECRET", '')


# Custom

SNAPSHOT = environ.get("SNAPSHOT")

SERVICE_NAME = environ.get("SERVICE_NAME")

HOSTNAME = environ.get("PRIMARY_HOSTNAME")


# BibXML-specific

DEFAULT_SEARCH_RESULT_LIMIT = 400
"""Default hard limit for found item count.

If the user hits this limit, they are expected to provide
a more precise query."""

LEGACY_DATASETS = {
    'bibxml': 'rfcs',
    'bibxml2': 'misc',
    'bibxml3': 'ids',
    'bibxml-id': 'ids',
    'bibxml4': {
        'dataset_id': 'w3c',
        'path_prefix': 'reference.W3C.',
    },
    'bibxml-w3c': {
        'dataset_id': 'w3c',
        'path_prefix': 'reference.W3C.',
    },
    'bibxml5': '3gpp',
    'bibxml6': 'ieee',
    'bibxml-ieee': 'ieee',
    'bibxml7': 'doi',
    'bibxml-doi': 'doi',
    'bibxml8': 'iana',
    'bibxml-iana': 'iana',
    'bibxml9': 'rfcsubseries',
    'bibxml-rfcsubseries': 'rfcsubseries',
    'bibxml-nist': {
        'dataset_id': 'nist',
        'ref_formatter':
            lambda legacy_ref:
                legacy_ref.replace('reference.', '').replace('.', '_'),
    },
}
"""
.. note:: This setting has been obsoleted as of v2022.1.28

Maps legacy dataset root as it appears under /public/rfc/
to known dataset ID(s) or configurations.

If legacy dataset name is mapped to a string,
the string is taken as known dataset ID, and configuration equivalent
of `'path_prefix': 'reference.'` from below
is in effect for this legacy dataset.

Dataset configuration, if provided,
must be a dictionary in one of the following shapes::

    { 'dataset_id': '<known_dataset_id>',
      'path_prefix': '<ref_prefix>' }

or::

    { 'dataset_id': '<known_dataset_id>',
      'ref_formatter': <function> }

or *(statically indexed datasets only)*::

    { 'dataset_id': '<known_dataset_id>',
      'query_builder': <function> }

Where:

- `path_prefix` can be used for simple formatting cases.
  The string would simply be cut off the start when obtaining the actual ref.
  (“Actual ref” is a canonical standard reference
  in one of the known bibxml-data datasets.)

  E.g. specifying `reference.W3C.` for dataset ID `w3c` means
  `/public/rfc/bibxml4/reference.W3C.WD-SWBP-SKOS-CORE-GUIDE-20051102.xml`
  would resolve to canonical ref `WD-SWBP-SKOS-CORE-GUIDE-20051102`
  in dataset `w3c` (corresponding to Git repository `bibxml-data-w3c`).

- Alternatively, a `ref_formatter` or `query_builder` function
  will be called on each request,
  receiving an URL-unquoted legacy ref string (the part before `.xml`).

  Either function must raise `RefNotFoundError`
  for an invalid or unrecognized legacy ref,
  which will result in HTTP 404.

- `ref_formatter` must return the actual ref.

  For example, specifying
  `lambda legacy_ref: legacy_ref.replace('reference.NIST', 'NIST').replace('.', '_')`
  would mean
  `/public/rfc/bibxml-nist/reference.NIST.TN.1968.xml`
  would work for dataset `nist` and ref `NIST_TN_1968`.

  The preceding example is equivalent to following
  `query_builder` configuration (see below)::

      lambda legacy_ref: Q(
          ref__iexact=
            legacy_ref.replace('reference.NIST', 'NIST').replace('.', '_'))

- `query_builder` must return a Django’s `Q` object,
  which will be used to query `RefData`.

  This option has no effect for external datasets.

  - If a single citation matches given Q,
    its full data is returned.
  - If multiple citations match, HTTP 404 will be returned.
  - If no citation matches, HTTP 404 will be returned.

  The following example::

      from django.db.models.query import Q

      def build_id_query(legacy_ref):
          parts = legacy_ref.split('-')
          if len(parts) > 1:
              rev = parts[-1]
              name = '-'.join(parts[0, len(parts) - 1])
              return Q(body__rev=rev) & Q(body__name=name)
          else:
              return Q(body__name=name)

      LEGACY_DATASETS = {
          'bibxml3': {
              'dataset_id': 'ids',
              'query_builder': build_id_query,
          },
      }

  Would mean that for a request to
  `/public/rfc/bibxml3/reference.SOME-NAME-123.xml`
  the service would try to return a citation in dataset `ids`
  where `body` contains key 'name' matching "SOME-NAME"
  _and_ key 'rev' matching "123".

.. note::

   If no BibXML representation exists on discovered citation,
   HTTP 404 is returned for given legacy path
   as if that citation does not exist.
"""

# TODO: Extract KNOWN_DATASETS from environment
KNOWN_DATASETS = [
    'rfcs',
    'ids',
    'rfcsubseries',
    'misc',
    'w3c',
    '3gpp',
    'ieee',
    'iana',
    'nist',
    'doi',
]
"""A list of known dataset IDs.
"""

EXTERNAL_DATASETS = [
    'doi',
]
"""A list of external datasets that we don’t index or search,
but support retrieval from.
"""

AUTHORITATIVE_DATASETS = [
    'rfcs',
    'ids',
    'rfcsubseries',
]
"""A list of authoritative datasets.
"""


# Further, specific to BibXML indexer

DATASET_SOURCE_OVERRIDES = {
    'ieee': {
        'relaton_data': {
            'repo_url': 'https://github.com/ietf-ribose/relaton-data-ieee',
        },
    },
}
"""Overrides dataset bibxml and/or relaton source. Supports partial override."""

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
"""

DATASET_TMP_ROOT = environ.get('DATASET_TMP_ROOT')
"""Where to keep fetched source data and data generated during indexing.
Should be a directory. No trailing slash."""
