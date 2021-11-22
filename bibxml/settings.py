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
                legacy_ref.replace('reference.NIST', 'NIST').replace('.', '_')
    },
}
"""Maps legacy dataset root as it appears under /public/rfc/
to known dataset ID(s) or configurations.

Dataset configuration, if provided, must be a dictionary like either::

    { 'dataset_id': '<known_dataset_id>',
      'path_prefix': '<ref_prefix>' }

or::

    { 'dataset_id': '<known_dataset_id>',
      'ref_formatter': <lambda function> }

Where:

- `ref_prefix` can be used for simple formatting cases.
  The string would simply be cut off the start when obtaining the actual ref.

  E.g. specifying `reference.W3C.` would mean
  `/public/rfc/bibxml4/reference.W3C.WD-SWBP-SKOS-CORE-GUIDE-20051102.xml`
  would work for dataset `w3c` and ref `WD-SWBP-SKOS-CORE-GUIDE-20051102`.

- `ref_formatter` can be used for simple formatting cases.
  The lambda would be called with legacy ref, and should return the actual ref.

  E.g. specifying `lambda legacy_ref: legacy_ref.replace('reference.NIST', 'NIST').replace('.', '_')`
  would mean
  `/public/rfc/bibxml-nist/reference.NIST.TN.1968.xml`
  would work for dataset `nist` and ref `NIST_TN_1968`.

If legacy dataset name is mapped to a string instead of a dictionary,
the string is taken as known dataset ID, and configuration equivalent
to `'path_prefix': 'reference.'` is in effect for this legacy dataset.
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
