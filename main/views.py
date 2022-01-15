"""View functions for citation browse GUI."""

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

from .exceptions import RefNotFoundError
from .models import RefData
from .indexed import get_indexed_ref, list_refs
from .indexed import build_citation_for_docid
from .external import get_doi_ref
from .util import BaseCitationSearchView


shared_context = dict(
    known_datasets=settings.KNOWN_DATASETS,
    indexed_datasets=[
        ds
        for ds in settings.KNOWN_DATASETS
        if ds not in settings.EXTERNAL_DATASETS],
    external_datasets=settings.EXTERNAL_DATASETS,
    authoritative_datasets=settings.AUTHORITATIVE_DATASETS,
    snapshot=settings.SNAPSHOT,
)
"""Shared context passed to GUI templates."""


def home(request):
    """Serves main landing page."""

    non_empty_datasets = (
        RefData.objects.values_list('dataset', flat=True).
        distinct())

    total_indexed_citations = RefData.objects.count()

    browsable_datasets = [
        ds_id
        for ds_id in shared_context['indexed_datasets']
        if ds_id in non_empty_datasets]

    return render(request, 'browse/home.html', dict(
        **shared_context,
        total_indexed_citations=total_indexed_citations,
        browsable_datasets=browsable_datasets,
    ))


# Browsing by document ID
# =======================

def browse_citation_by_docid(request, doctype=None, docid=None):
    """
    Reads ``docid`` and ``doctype`` from GET query,
    uses :func:`main.indexed.build_citation_for_docid`
    to get a bibliographic item and in case of success
    renders the citation details template.

    If bibliographic item could not be built
    (no matching document ID found across Relaton sources),
    queues an ``info``-level message
    and redirects to search page,
    passing space-separated document type and ID as query.
    """

    doctype, docid = request.GET.get('doctype', None), request.GET.get('docid')

    if not docid:
        return HttpResponseBadRequest("Missing document ID")

    try:
        citation = build_citation_for_docid(docid, doctype)

    except RefNotFoundError:
        search_query = QueryDict('', mutable=True)
        search_query.update({
            'query': '{}'.format(docid),
        })
        messages.info(
            request,
            "Could not find a bibliographic item "
            "exactly matching requested document identifier "
            "with ID “{}” (type {}), "
            "you were redirected to search".format(
                docid,
                doctype or "unspecified"))
        return redirect('{}?{}'.format(
            reverse('search_citations'),
            search_query.urlencode(),
        ))

    else:
        result = unpack_dataclasses(citation.dict())
        return render(request, 'browse/citation_details.html', dict(
            data=result,
            **shared_context,
        ))


class CitationSearchResultListView(MultipleObjectTemplateResponseMixin,
                                   BaseCitationSearchView):

    template_name = 'browse/search_citations.html'
    show_all_by_default = True

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            **shared_context,
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

    if not ref:
        return HttpResponseBadRequest(
            "Missing reference to fetch")

    if dataset_id not in settings.EXTERNAL_DATASETS:
        return HttpResponseBadRequest(
            "Unknown dataset requested")

    if dataset_id == 'doi':
        try:
            data = unpack_dataclasses(get_doi_ref(ref).dict())
        except RuntimeError as exc:
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
            "Unsupported external dataset {}".format(dataset_id))

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
    paginate_by = 20
    template_name = 'browse/dataset.html'

    def get_queryset(self) -> QuerySet[RefData]:
        return list_refs(self.kwargs['dataset_id'])

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            dataset_id=self.kwargs['dataset_id'],
            **shared_context,
        )
