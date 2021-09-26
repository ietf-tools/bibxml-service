from django.conf import settings
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt

from . import views


_LIBS = settings.INDEXABLE_DATASETS
_LIBS.append("doi")
_RE_LIBS = f'(?P<lib>{"|".join(_LIBS)})'

urlpatterns = [
    path('v1/', views.index, name='api_index'),
    path('v1/search', csrf_exempt(views.search), name='api_search'),
    re_path(
        f'^v1/ref/{_RE_LIBS}/(?P<ref>[A-z0-9\_\-\.\/]+)',
        views.get_ref,
        name='api_get_ref'
    ),
]

