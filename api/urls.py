from django.urls import include, path
from django.urls import include, path, re_path

from django.conf import settings

from . import views

from django.views.decorators.csrf import csrf_exempt
    

_libs = settings.INDEXABLE_DATASETS
_libs.append("doi")
re_libs = f'(?P<lib>{"|".join(_libs)})'

urlpatterns = [
    path('v1/', views.index, name='api_index'),
    path('v1/search', csrf_exempt(views.search), name='api_search'),
    re_path(f'^v1/ref/{re_libs}/(?P<ref>[A-z0-9\_\-\.\/]+)', views.get_ref, name='api_get_ref'),
]

