"""View functions for citation browse GUI."""

from urllib.parse import unquote_plus

from django.db.models.query import QuerySet
from django.http.response import HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render
from django.conf import settings
from django.views.generic.list import ListView

from .exceptions import RefNotFoundError
from .models import RefData
from .indexed import get_indexed_ref, list_refs, search_refs


shared_context = dict(
    known_datasets=settings.KNOWN_DATASETS,
    external_datasets=settings.EXTERNAL_DATASETS,
    authoritative_datasets=settings.AUTHORITATIVE_DATASETS,
)


def browse_citations(request, dataset_id=None, ref=None):
    if dataset_id is not None:
        if ref is not None:
            try:
                data = get_indexed_ref(dataset_id, ref)
            except RefNotFoundError:
                return HttpResponseNotFound("Requested reference not found")
            else:
                return render(request, 'browse_citation.html', dict(
                    dataset_id=dataset_id,
                    ref=ref,
                    data=data,
                    **shared_context,
                ))
        return render(request, 'browse_dataset.html', dict(
            dataset_id=dataset_id,
            citations=list_refs(dataset_id),
            **shared_context,
        ))
    return render(request, 'browse.html', dict(
        **shared_context,
    ))


class CitationSearchResultListView(ListView):
    model = RefData
    paginate_by = 20
    template_name = 'search_citations.html'

    def get_queryset(self) -> QuerySet[RefData]:
        query = self.request.GET.get('query', None)
        if query:
            return search_refs(unquote_plus(query))
        else:
            return HttpResponseBadRequest("No search query specified.")

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            query=self.request.GET.get('query'),
            **shared_context,
        )


class CitationListView(ListView):
    model = RefData
    paginate_by = 20
    template_name = 'browse_dataset.html'

    def get_queryset(self) -> QuerySet[RefData]:
        return list_refs(self.kwargs['dataset_id'])

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            dataset_id=self.kwargs['dataset_id'],
            **shared_context,
        )
