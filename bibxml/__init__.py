"""Django project module."""

from django.core import checks
from .env_checker import env_checker

checks.register(env_checker)
