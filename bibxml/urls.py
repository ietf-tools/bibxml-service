from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.urls import path, include
from django.views.decorators.http import require_POST, require_safe

from main import api as public_api, views as public_views
from management import api as mgmt_api, views as mgmt_views
from management import auth
from xml2rfc_compat import fetchers as xml2rfc_fetchers
from xml2rfc_compat.aliases import get_aliases as get_xml2rfc_aliases
from xml2rfc_compat.urls import make_xml2rfc_path_pattern
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
    path('public/rfc/', include([
        *make_xml2rfc_path_pattern(
            ['bibxml', *get_xml2rfc_aliases('bibxml')],
            xml2rfc_fetchers.rfcs),
        *make_xml2rfc_path_pattern(
            ['bibxml2', *get_xml2rfc_aliases('bibxml2')],
            xml2rfc_fetchers.misc),
        *make_xml2rfc_path_pattern(
            ['bibxml3', *get_xml2rfc_aliases('bibxml3')],
            xml2rfc_fetchers.internet_drafts),
        *make_xml2rfc_path_pattern(
            ['bibxml4', *get_xml2rfc_aliases('bibxml4')],
            xml2rfc_fetchers.w3c),
        *make_xml2rfc_path_pattern(
            ['bibxml5', *get_xml2rfc_aliases('bibxml5')],
            xml2rfc_fetchers.threegpp),
        *make_xml2rfc_path_pattern(
            ['bibxml6', *get_xml2rfc_aliases('bibxml6')],
            xml2rfc_fetchers.ieee),
        *make_xml2rfc_path_pattern(
            ['bibxml7', *get_xml2rfc_aliases('bibxml7')],
            xml2rfc_fetchers.doi),
        *make_xml2rfc_path_pattern(
            ['bibxml8', *get_xml2rfc_aliases('bibxml8')],
            xml2rfc_fetchers.iana),
        *make_xml2rfc_path_pattern(
            ['bibxml9', *get_xml2rfc_aliases('bibxml9')],
            xml2rfc_fetchers.rfcsubseries),
        *make_xml2rfc_path_pattern(
            ['bibxml-nist'],
            xml2rfc_fetchers.nist),
    ])),

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
