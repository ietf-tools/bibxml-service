from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('public/rfc/', include('api.legacy_urls')),
    path('openapi.yaml', views.openapi_spec),
]
