from django.contrib import admin
from django.views.decorators.csrf import csrf_exempt
from django.urls import path, include
from django.views.decorators.http import require_POST, require_safe

from main import api, views

from .views import openapi_spec


urlpatterns = [
    path('admin/', admin.site.urls),

    path('openapi.yaml', require_safe(openapi_spec)),

    path('api/', include([
        path('v1/', include([
            path('',
                 require_safe(api.index),
                 name='api_index'),
            path('search/',
                 csrf_exempt(require_POST(api.search)),
                 name='api_search'),
            path('ref/', include([
                path('doi/<ref>/', api.get_doi_ref, name='api_get_doi_ref'),
                path('<dataset_name>/<ref>/', api.get_ref, name='api_get_ref'),
            ])),
        ])),
    ])),

    path('public/rfc/', include([
        path('<legacy_dataset_name>/reference.<ref>.xml/',
             api.get_ref_by_legacy_path,
             name='api_get_ref_by_legacy_path'),
    ])),

    path('', include([
        path('',
             require_safe(views.browse_citations),
             name='browse'),
        path('search/',
             require_safe(views.CitationSearchResultListView.as_view()),
             name='search_citations'),
        path('<dataset_id>/', include([
            path('',
                 require_safe(views.CitationListView.as_view()),
                 name='browse_dataset'),
            path('<ref>/',
                 require_safe(views.browse_citations),
                 name='browse_citation'),
        ])),
    ])),
]
