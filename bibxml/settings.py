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


# BibXML-specific

LEGACY_DATASETS = {
    'bibxml': 'rfcs',
    'bibxml2': 'misc',
    'bibxml3': 'ids',
    'bibxml-id': 'ids',
    'bibxml4': 'w3c',
    'bibxml5': '3gpp',
    'bibxml6': 'ieee',
    'bibxml7': 'doi',
    'bibxml8': 'iana',
    'bibxml9': 'rfcsubseries',
    'bibxml-rfcsubseries': 'rfcsubseries',
    'bibxml-nist': 'nist',
}
"""Maps legacy dataset root as it appears under /public/rfc/
to known dataset ID(s)."""

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

INDEXABLE_DATASETS = [
    "ecma",
    "nist",
    "ietf",
    "itu-r",
    "calconnect",
    "cie",
    "iso",
    "bipm",
    "iho"
]
"""
DEPRECATED.

List of supported datasets
Need to be matched with Indexer service
(maybe set this value from ENV or substitute on deploy?)
"""


MAX_RECORDS_PER_RESPONSE = 100
"""Limit results in /search/ per request."""
