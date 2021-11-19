"""View functions for citation browse GUI."""

from django.db.models.query import QuerySet
from django.shortcuts import render
from django.conf import settings
from django.views.generic.list import ListView

from main.models import RefData

from .indexed import RefDataManager, get_indexed_ref, list_refs


shared_context = dict(
    known_datasets=settings.KNOWN_DATASETS,
)


def browse_citations(request, dataset_id=None, ref=None):
    if dataset_id is not None:
        if ref is not None:
            return render(request, 'browse_citation.html', dict(
                dataset_id=dataset_id,
                ref=ref,
                citation=get_indexed_ref(dataset_id, ref),
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


class CitationListView(ListView):
    model = RefData
    paginate_by = 20
    template_name = 'browse_dataset.html'

    def get_queryset(self) -> QuerySet[RefData]:
        return RefDataManager.filter(
            dataset=self.kwargs['dataset_id'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset_id'] = self.kwargs['dataset_id']

        return dict(
            **context,
            **shared_context,
        )
