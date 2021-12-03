from pathlib import Path
from os import environ, path


BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environ.get("DJANGO_SECRET")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(environ.get("DEBUG", default=0)) == 1

ALLOWED_HOSTS = [
    environ.get("PRIMARY_HOSTNAME"),
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main.app.Config',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bibxml.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'bibxml-service',
    },
    'index': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': environ.get('DB_NAME'),
        'USER': environ.get('DB_USER'),
        'PASSWORD': environ.get('DB_SECRET'),
        'HOST': environ.get('DB_HOST'),
        'PORT': int(environ.get('DB_PORT')),
    }
}


# NOTE: This project isn’t intended to be used with conventional Django auth,
# hence this setting is empty.
AUTH_PASSWORD_VALIDATORS = []


# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [
    BASE_DIR / 'static'
]
STATIC_ROOT = BASE_DIR / 'build' / 'static'


# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Version

SNAPSHOT = {
    'hash': environ.get('SNAPSHOT_HASH', None),
    'time': environ.get('SNAPSHOT_TIME', None),
}


# BibXML-specific

LEGACY_DATASETS = {
    'bibxml': 'rfcs',
    'bibxml2': 'misc',
    'bibxml3': 'ids',
    'bibxml-id': 'ids',
    'bibxml4': {
        'dataset_id': 'w3c',
        'path_prefix': 'reference.W3C.',
    },
    'bibxml5': '3gpp',
    'bibxml6': 'ieee',
    'bibxml7': 'doi',
    'bibxml8': 'iana',
    'bibxml9': 'rfcsubseries',
    'bibxml-rfcsubseries': 'rfcsubseries',
    'bibxml-nist': {
        'dataset_id': 'nist',
        'ref_formatter':
            lambda legacy_ref:
                legacy_ref.replace('reference.', '').replace('.', '_'),
    },
}
"""Maps legacy dataset root as it appears under /public/rfc/
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
"""A list of known dataset IDs. NOTE: Keep in sync with bibxml-indexer.
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
