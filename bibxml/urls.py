from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.urls import path, include
from django.views.decorators.http import require_POST, require_safe
from django.views.generic.base import TemplateView

from main import api as public_api, views as public_views
from management import api as mgmt_api, views as mgmt_views
from management import auth
from xml2rfc_compat import management_views as xml2rfc_views
from . import xml2rfc_adapters  # Imported for registration side-effect
from xml2rfc_compat.urls import get_urls as get_xml2rfc_urls
from datatracker import auth as dt_auth
from datatracker import oauth as dt_oauth
from prometheus.views import metrics as prometheus_metrics

from . import views, error_views


handler403 = error_views.not_authorized
handler404 = error_views.not_found
handler500 = error_views.server_error

default_ttl = (
    getattr(settings, 'DEFAULT_CACHE_SECONDS', 3600)
    if not settings.DEBUG
    else 0)


urlpatterns = [

    path('__debug__/', include('debug_toolbar.urls')),
    path('metrics/', auth.basic(prometheus_metrics)),

    path('about', never_cache(require_safe(
        views.about
    )), name='about'),

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
            path('', require_safe(
                views.readable_openapi_spec_main
            ), name='api_index'),

            # Public endpoints

            path('json-schema/<ref>/', require_safe(
                public_api.json_schema
            ), name='json_schema'),

            # We let search results to be cached on a different level
            path('search/<query>/', require_safe(dt_auth.api(
                public_api.CitationSearchResultListView.as_view()
            )), name='api_search'),

            path('by-docid/', require_safe(dt_auth.api(
                public_api.get_by_docid
            )), name='api_get_by_docid'),

            path('ref/', include([
                path('doi/<ref>/', require_safe(dt_auth.api(
                    public_api.get_doi_ref
                )), name='api_get_doi_ref'),

                # Obsolete
                path('<dataset_name>/<ref>/', require_safe(dt_auth.api(
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
    path(settings.XML2RFC_PATH_PREFIX, include(get_xml2rfc_urls())),

    # Management GUI
    path('management/', include([
        path('', require_safe(auth.basic(never_cache(
            mgmt_views.home
        ))), name='manage'),

        path('indexable-sources/', include([
            path('', require_safe(auth.basic(never_cache(
                mgmt_views.datasets
            ))), name='manage_indexable_sources'),
            path('<dataset_id>/', include([
                path('', require_safe(auth.basic(never_cache(
                    mgmt_views.dataset
                ))), name='manage_indexable_source'),
            ])),
        ])),

        path('tasks/', include([
            path('<task_id>/', include([
                path('', require_safe(auth.basic(never_cache(
                    mgmt_views.indexing_task
                ))), name='manage_indexing_task'),
            ])),
        ])),

        path('xml2rfc-compat/', include([
            path('', require_safe(auth.basic(never_cache(
                xml2rfc_views.DirectoryOverview.as_view(
                    template_name='management/xml2rfc.html',
                )
            ))), name='manage_xml2rfc'),
            path('<path:subpath>/', require_safe(auth.basic(never_cache(
                xml2rfc_views.ExploreDirectory.as_view(
                    template_name='management/xml2rfc_directory.html',
                )
            ))), name='manage_xml2rfc_directory'),
        ])),
    ])),

    # robots.txt
    path('robots.txt',TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain')),

    # Main GUI
    path('', include([

        path('', require_safe(
            public_views.home
        ), name='browse'),

        path('datatracker-auth/', include([
            path('', require_safe(never_cache(
                dt_oauth.initiate
            )), name='datatracker_oauth_initiate'),
            path('callback/', require_safe(never_cache(
                dt_oauth.handle_callback
            )), name='datatracker_oauth_callback'),
            path('log-out/', require_safe(never_cache(
                dt_oauth.log_out
            )), name='datatracker_oauth_logout'),
        ])),

        path('get-bibliographic-item/', never_cache(require_safe(
            public_views.smart_query
        )), name='get_bibliographic_item'),

        # We let search results to be cached on a different level
        path('search/', never_cache(require_safe(
            public_views.CitationSearchResultListView.as_view()
        )), name='search_citations'),

        path('get-one/', include([
            path('by-docid/', require_safe(
                public_views.browse_citation_by_docid
            ), name='get_citation_by_docid'),

            path('export/', require_safe(
                public_views.export_citation
            ), name='export_citation'),

            # We let external source retrieval logic to cache this one:
            path('external/<dataset_id>/', never_cache(require_safe(
                public_views.browse_external_reference
            )), name='get_external_citation'),
        ])),

        path('indexed-sources/', include([
            path('relaton-data-<dataset_id>/', include([
                path('', never_cache(require_safe(
                    public_views.IndexedDatasetCitationListView.as_view()
                )), name='browse_dataset'),
                path('<ref>/', never_cache(require_safe(
                    public_views.browse_indexed_reference
                )), name='browse_indexed_ref'),
            ])),
        ])),

        path('external-sources/', include([
            path('<dataset_id>/', include([
                path('<path:ref>/', require_safe(
                    public_views.browse_external_reference
                ), name='browse_external_citation'),
            ])),
        ])),
    ])),

]
