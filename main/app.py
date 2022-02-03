import importlib
from django.apps import AppConfig


class Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        importlib.import_module('main.sources')
