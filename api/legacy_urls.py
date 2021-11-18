from django.urls import re_path
from . import views


urlpatterns = [
    re_path(
        r'(?P<legacy_dataset_name>[\w-]+)/'
        r'reference\.(?P<ref>[A-z0-9\_\-\.\/]+)\.xml$',
        views.get_ref_by_legacy_path,
        name="api_get_ref_by_legacy_path",
    ),
]
