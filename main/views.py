"""View functions for citation browse GUI."""

import logging
from math import log as log_, floor
from urllib.parse import unquote_plus

from django.db.models.query import QuerySet
from django.urls import reverse
from django.http import QueryDict
from django.http.response import Http404
from django.http.response import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.conf import settings
from django.views.generic.list import ListView
from django.views.generic.list import MultipleObjectTemplateResponseMixin
from django.contrib import messages

from bibxml import error_views
from common.pydantic import unpack_dataclasses
from prometheus import metrics
from sources.exceptions import RefNotFoundError
from doi import get_doi_ref

from .models import RefData
from .query import get_indexed_ref, list_refs
from .query import build_citation_for_docid
from .util import BaseCitationSearchView
from .util import QUERY_FORMAT_LABELS


log = logging.getLogger(__name__)


shared_context = dict(
    supported_search_formats=[
        (format, QUERY_FORMAT_LABELS.get(format, format))
        for format in BaseCitationSearchView.supported_query_formats
    ],
)
"""Shared context passed to GUI templates."""


def home(request):
    """Serves main landing page."""

    metrics.gui_home_page_hits.inc()

    non_empty_datasets = (
        RefData.objects.values_list('dataset', flat=True).
        distinct())

    total_indexed_citations = RefData.objects.count()
    units = ('', 'k', 'M', 'G', 'T', 'P')
    factor = 1000.0
    magnitude = int(floor(log_(max(abs(total_indexed_citations), 1), factor)))
    total_indexed_human = '%.2f%s' % (
        total_indexed_citations / factor**magnitude,
        units[magnitude],
    )

    browsable_datasets = [
        ds_id
        for ds_id in settings.RELATON_DATASETS
        if ds_id in non_empty_datasets]

    return render(request, 'browse/home.html', dict(
        **shared_context,
        total_indexed_human=total_indexed_human,
        browsable_datasets=browsable_datasets,
    ))


def smart_query(request):
    """Tries to find a bibliographic item
    from search query given in ``query`` GET parameter,
    with optional ``query_format``."""

    query = request.GET.get('query', None)
    query_format = request.GET.get('query_format', None)

    if not query:
        messages.warning(request, "Query was not provided.")
        return HttpResponseRedirect(request.headers.get('referer', '/'))

    if not query_format:
        querydict = QueryDict('', mutable=True)
        querydict.update({'docid': query})
        request.GET = querydict
        return browse_citation_by_docid(request)

    else:
        return redirect('{}?{}'.format(
            reverse('search_citations'),
            request.GET.urlencode(),
        ))


# Browsing by document ID
# =======================

def browse_citation_by_docid(request):
    """
    Reads ``docid`` (and optionally ``doctype``) from GET query,
    uses :func:`main.indexed.build_citation_for_docid`
    to get a bibliographic item and in case of success
    renders the citation details template.

    If bibliographic item could not be built
    (no matching document ID found across Relaton sources),
    tries to infer query format,
    queues an ``info``-level message
    and redirects to search page
    passing given document ID as query (``doctype`` in that case is ignored).
    """

    doctype, docid = request.GET.get('doctype', None), request.GET.get('docid')

    if not docid:
        return HttpResponseBadRequest("Missing document ID")

    try:
        citation = build_citation_for_docid(
            docid.strip().strip('.').strip('.xml'),
            doctype.strip() if doctype else None,
            strict=False)

    except RefNotFoundError as e:
        log.warning("Could not locate item by docid: %s, %s", docid, doctype)
        metrics.gui_bibitem_hits.labels(docid, 'fallback_to_search').inc()

        messages.info(
            request,
            "Could not find a bibliographic item "
            f"exactly matching given document identifier (err: {e}), "
            "trying search instead.")

        query = docid
        search_querydict = QueryDict('', mutable=True)
        search_querydict.update({
            'query': '{}'.format(query),
            'allow_format_fallback': True,
            'bypass_cache': True,
        })
        return redirect('{}?{}'.format(
            reverse('search_citations'),
            search_querydict.urlencode(),
        ))

    else:
        result = unpack_dataclasses(citation.dict())
        metrics.gui_bibitem_hits.labels(docid, 'success').inc()
        return render(request, 'browse/citation_details.html', dict(
            data=result,
            **shared_context,
        ))


class CitationSearchResultListView(MultipleObjectTemplateResponseMixin,
                                   BaseCitationSearchView):

    template_name = 'browse/search_citations.html'
    metric_counter = metrics.gui_search_hits

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            **shared_context,
            total_indexed=RefData.objects.count(),
        )


# External sources
# ================

def external_dataset(request, dataset_id):
    return render(request, 'browse/dataset.html', dict(
        dataset_id=dataset_id,
        **shared_context,
    ))


def browse_external_reference(request, dataset_id):
    ref = request.GET.get('ref')

    if ref:
        if dataset_id not in settings.EXTERNAL_DATASETS:
            return HttpResponseBadRequest("Unknown dataset requested")

        if dataset_id == 'doi':
            try:
                _data = get_doi_ref(ref.strip()).dict()
                data = unpack_dataclasses(_data)
            except RuntimeError as exc:
                log.exception(
                    "Failed to retrieve or unpack "
                    "external bibliographic item %s from %s",
                    ref,
                    dataset_id)
                messages.error(
                    request,
                    "Couldn’t retrieve citation: {}".format(
                        str(exc)))
            else:
                return render(request, 'browse/citation_details.html', dict(
                    dataset_id=dataset_id,
                    ref=ref,
                    data=data,
                    **shared_context,
                ))
        else:
            messages.error(
                request,
                "Unsupported external source {}".format(dataset_id))
    else:
        messages.error(
            request,
            "Did not receive a reference for external lookup")

    # If we’re here, it must’ve failed
    return HttpResponseRedirect(request.headers.get('referer', '/'))


# Browsing by dataset (semi-internal)
# ===================================

def browse_indexed_reference(request, dataset_id, ref):
    parsed_ref = unquote_plus(ref)

    try:
        if dataset_id == 'doi':
            try:
                data = get_doi_ref(parsed_ref)
            except Exception:
                return error_views.server_error(request)
        else:
            data = get_indexed_ref(dataset_id, parsed_ref)

    except RefNotFoundError:
        raise Http404(
            "Requested reference “{}” "
            "could not be found in dataset “{}” "
            "(or external source is unavailable)".format(
                parsed_ref,
                dataset_id))

    else:
        return render(request, 'browse/citation_details.html', dict(
            dataset_id=dataset_id,
            ref=ref,
            data=data,
            **shared_context,
        ))


class IndexedDatasetCitationListView(ListView):
    model = RefData
    paginate_by = 10
    template_name = 'browse/dataset.html'

    def get_queryset(self) -> QuerySet[RefData]:
        return list_refs(self.kwargs['dataset_id'])

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            dataset_id=self.kwargs['dataset_id'],
            **shared_context,
        )
