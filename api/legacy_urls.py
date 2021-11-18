from django.urls import re_path
from . import views


urlpatterns = [
    re_path(
        r'(?P<legacy_dataset_name>[\w-]+)/'
        r'reference\.(?P<legacy_ref>[A-z0-9\_\-\.\/]+)\.xml$',
        views.get_legacy_ref,
        name="api_get_legacy_ref",
    ),
]
