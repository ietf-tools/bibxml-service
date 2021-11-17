from django.urls import path, re_path
from django.views.decorators.csrf import csrf_exempt
from . import views


urlpatterns = [
    path('v1/', views.index, name='api_index'),
    path('v1/search', csrf_exempt(views.search), name='api_search'),
    re_path(
        r'^v1/ref/(?P<dataset_name>[\w-]+)/(?P<ref>[A-z0-9\_\-\.\/]+)',
        views.get_ref,
        name='api_get_ref'
    ),
]
