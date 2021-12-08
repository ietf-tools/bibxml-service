from django.contrib import admin
from django.views.decorators.csrf import csrf_exempt
from django.urls import path, include
from django.views.decorators.http import require_POST, require_safe

from main import api, views
from management import api as mgmt_api
from management import views as mgmt_views
from management.auth import auth, basic_auth

from .views import openapi_spec, legacy_openapi_spec


urlpatterns = [
    path('admin/', admin.site.urls),

    path('openapi.yaml', require_safe(openapi_spec)),
    path('openapi-legacy.yaml', require_safe(legacy_openapi_spec)),

    path('api/', include([
        path('v1/', include([
            path('',
                 require_safe(api.index),
                 name='api_index'),
            path('search/<query>/',
                 csrf_exempt(require_safe(
                     api.CitationSearchResultListView.as_view())
                 ),
                 name='api_search'),
            path('ref/', include([
                path('doi/<ref>/', api.get_doi_ref, name='api_get_doi_ref'),
                path('<dataset_name>/<ref>/', api.get_ref, name='api_get_ref'),
            ])),
            path('management/', include([
                path('<dataset_name>/', include([
                    path('reindex/',
                         csrf_exempt(require_POST(auth(mgmt_api.run_indexer))),
                         name='api_run_indexer'),
                    path('reset-index/',
                         csrf_exempt(require_POST(auth(mgmt_api.reset_index))),
                         name='api_reset_index'),
                    path('get-index-status/',
                         require_safe(auth(mgmt_api.indexer_status)),
                         name='api_indexer_status'),
                ])),
            ])),
            path('tasks/', include([
                path('<task_id>/stop/',
                     csrf_exempt(require_POST(auth(mgmt_api.stop_task))),
                     name='api_stop_task'),
                path('stop-all/',
                     csrf_exempt(require_POST(auth(mgmt_api.stop_all_tasks))),
                     name='api_stop_all_tasks'),
            ])),
        ])),
    ])),

    path('compatibility-api/',
         require_safe(api.index_legacy),
         name='compat_api_index'),
    path('public/rfc/', include([
        path('<legacy_dataset_name>/<legacy_reference>.xml',
             api.get_ref_by_legacy_path,
             name='compat_api_get_ref_by_legacy_path'),
    ])),

    path('', include([
        path('',
             require_safe(views.browse_citations),
             name='browse'),
        path('search/',
             require_safe(views.CitationSearchResultListView.as_view()),
             name='search_citations'),
        path('external/<dataset_id>/',
             require_safe(views.browse_external_citation),
             name='browse_external_citation'),
        path('<dataset_id>/', include([
            path('',
                 require_safe(views.CitationListView.as_view()),
                 name='browse_dataset'),
            path('<ref>/',
                 require_safe(views.browse_citations),
                 name='browse_citation'),
        ])),
        path('management/', include([
            path('',
                 require_safe(basic_auth(mgmt_views.manage)),
                 name='manage'),
            path('<dataset_id>/', include([
                path('',
                     require_safe(basic_auth(mgmt_views.manage_dataset)),
                     name='manage_dataset'),
            ])),
        ])),
    ])),
]
