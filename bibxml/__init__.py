"""Django project module."""

from django.core import checks
from .env_checker import env_checker

checks.register(env_checker)


from bib_models import serializers
from xml2rfc_compat.serializer import to_xml_string

serializers.register('bibxml', 'application/xml')(to_xml_string)
