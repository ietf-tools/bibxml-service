from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.urls import path, include
from django.views.decorators.http import require_POST, require_safe

from main import api as public_api, views as public_views
from management import api as mgmt_api, views as mgmt_views
from management import auth

from . import views, error_views


handler403 = error_views.not_authorized
handler404 = error_views.not_found
handler500 = error_views.server_error


urlpatterns = [

    path('__debug__/', include('debug_toolbar.urls')),

    # API specs
    path('openapi.yaml', never_cache(require_safe(
        views.openapi_spec
    )), name='openapi_spec_main'),
    path('openapi-legacy.yaml', never_cache(require_safe(
        views.legacy_openapi_spec
    )), name='openapi_spec_legacy'),
    path('api-spec/<spec>/', never_cache(require_safe(
        views.readable_openapi_spec
    )), name='openapi_readable_spec'),

    # Main API
    path('api/', include([
        path('v1/', include([
            path('', never_cache(require_safe(
                views.readable_openapi_spec_main
            )), name='api_index'),

            # Public endpoints

            # We let search results to be cached on a different level
            path('search/<query>/', never_cache(require_safe(
                public_api.CitationSearchResultListView.as_view()
            )), name='api_search'),

            path('by-docid/', require_safe(
                public_api.get_by_docid
            ), name='api_get_by_docid'),

            path('ref/', include([
                path('doi/<ref>/', never_cache(require_safe(
                    public_api.get_doi_ref
                )), name='api_get_doi_ref'),
                path('<dataset_name>/<ref>/', never_cache(require_safe(
                    public_api.get_ref
                )), name='api_get_ref'),
            ])),

            # Management endpoints
            path('management/', include([
                path('tasks/', include([
                    path('<task_id>/stop/', csrf_exempt(require_POST(auth.api(
                        mgmt_api.stop_task
                    ))), name='api_stop_task'),
                    path('stop-all/', csrf_exempt(require_POST(auth.api(
                        mgmt_api.stop_all_tasks
                    ))), name='api_stop_all_tasks'),
                ])),
                path('<dataset_name>/', include([
                    path('status/', never_cache(require_safe(
                        mgmt_api.indexer_status
                    )), name='api_indexer_status'),
                    path('reindex/', csrf_exempt(require_POST(auth.api(
                        mgmt_api.run_indexer
                    ))), name='api_run_indexer'),
                    path('reset-index/', csrf_exempt(require_POST(auth.api(
                        mgmt_api.reset_index
                    ))), name='api_reset_index'),
                ])),
            ])),
        ])),
    ])),

    # Compatibility API
    path('public/rfc/', include([
        path(
            '<legacy_dataset_name>/<legacy_reference>.xml',
            never_cache(require_safe(
                public_api.get_ref_by_legacy_path
            )),
            name='compat_api_get_ref_by_legacy_path',
        ),
    ])),

    # Main GUI
    path('', include([

        path('', require_safe(
            public_views.home
        ), name='browse'),

        path('management/', include([
            path('', require_safe(auth.basic(never_cache(
                mgmt_views.manage
            ))), name='manage'),
            path('<dataset_id>/', include([
                path('', require_safe(auth.basic(never_cache(
                    mgmt_views.manage_dataset
                ))), name='manage_dataset'),
            ])),
        ])),

        # We let search results to be cached on a different level
        path('search/', never_cache(require_safe(
            public_views.CitationSearchResultListView.as_view()
        )), name='search_citations'),

        path('get-one/', include([
            path('by-docid/', require_safe(
                public_views.browse_citation_by_docid
            ), name='get_citation_by_docid'),

            # We let external source retrieval logic to cache this one:
            path('external/<dataset_id>/', never_cache(require_safe(
                public_views.browse_external_reference
            )), name='get_external_citation'),
        ])),

        path('indexed-sources/', include([
            path('<dataset_id>/', include([
                path('', never_cache(require_safe(
                    public_views.IndexedDatasetCitationListView.as_view()
                )), name='browse_dataset'),
                path('<ref>/', never_cache(require_safe(
                    public_views.browse_indexed_reference
                )), name='browse_citation'),
            ])),
        ])),

        path('external-sources/', include([
            path('<dataset_id>/', include([
                path('', never_cache(require_safe(
                    public_views.external_dataset
                )), name='browse_external_dataset'),
                path('<path:ref>/', require_safe(
                    public_views.browse_external_reference
                ), name='browse_external_citation'),
            ])),
        ])),
    ])),

]
