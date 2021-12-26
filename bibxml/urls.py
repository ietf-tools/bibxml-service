from django.views.decorators.csrf import csrf_exempt
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

    # API specs
    path('openapi.yaml', require_safe(
        views.openapi_spec
    ), name='openapi_spec_main'),
    path('openapi-legacy.yaml', require_safe(
        views.legacy_openapi_spec
    ), name='openapi_spec_legacy'),
    path('api-spec/<spec>/', require_safe(
        views.readable_openapi_spec
    ), name='openapi_readable_spec'),

    # Main API
    path('api/', include([
        path('v1/', include([
            path('', require_safe(
                views.readable_openapi_spec_main
            ), name='api_index'),

            # Public endpoints
            path('search/<query>/', require_safe(
                public_api.CitationSearchResultListView.as_view()
            ), name='api_search'),
            path('ref/', include([
                path('doi/<ref>/', require_safe(
                    public_api.get_doi_ref
                ), name='api_get_doi_ref'),
                path('<dataset_name>/<ref>/', require_safe(
                    public_api.get_ref
                ), name='api_get_ref'),
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
                    path('status/', require_safe(
                        mgmt_api.indexer_status
                    ), name='api_indexer_status'),
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
        path('<legacy_dataset_name>/<legacy_reference>.xml', require_safe(
            public_api.get_ref_by_legacy_path
        ), name='compat_api_get_ref_by_legacy_path'),
    ])),

    # Main GUI
    path('', include([

        path('', require_safe(
            public_views.home
        ), name='browse'),

        path('management/', include([
            path('', require_safe(auth.basic(
                mgmt_views.manage
            )), name='manage'),
            path('<dataset_id>/', include([
                path('', require_safe(auth.basic(
                    mgmt_views.manage_dataset
                )), name='manage_dataset'),
            ])),
        ])),

        path('types/', include([
            path('<doctype>/', include([
                path('<path:docid>/', require_safe(
                    public_views.browse_citation_by_docid
                ), name='browse_citation_by_docid'),
            ])),
        ])),

        path('search/', require_safe(
            public_views.CitationSearchResultListView.as_view()
        ), name='search_citations'),

        path('load-and-redirect/', include([
            path('by-docid/', require_safe(
                public_views.browse_citation_by_docid
            ), name='load_citation_by_docid'),
            path('external/<dataset_id>/', require_safe(
                public_views.browse_external_reference
            ), name='load_external_citation'),
        ])),

        path('indexed-sources/', include([
            path('<dataset_id>/', include([
                path('', require_safe(
                    public_views.IndexedDatasetCitationListView.as_view()
                ), name='browse_dataset'),
                path('<ref>/', require_safe(
                    public_views.browse_indexed_reference
                ), name='browse_citation'),
            ])),
        ])),

        path('external-sources/', include([
            path('<dataset_id>/', include([
                path('', require_safe(
                    public_views.external_dataset
                ), name='browse_external_dataset'),
                path('<path:ref>/', require_safe(
                    public_views.browse_external_reference
                ), name='browse_external_citation'),
            ])),
        ])),
    ])),

]
