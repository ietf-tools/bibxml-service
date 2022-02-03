import importlib
from django.apps import AppConfig


class Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'xml2rfc_compat'

    def ready(self):
        # Import modules to make things register as a side effect
        importlib.import_module('xml2rfc_compat.source')
        importlib.import_module('xml2rfc_compat.serializer')
