"""View functions for citation retrieval GUI."""

import logging
from math import log as log_, floor
from urllib.parse import unquote_plus
import json

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

from pydantic import ValidationError

from common.pydantic import unpack_dataclasses
from prometheus import metrics
from bib_models import serializers, BibliographicItem
from xml2rfc_compat import adapters as xml2rfc_adapters

from .models import RefData
from .query import get_indexed_item, list_refs
from .query import build_citation_for_docid
from .search import BaseCitationSearchView
from .search import QUERY_FORMAT_LABELS
from .exceptions import RefNotFoundError
from .api import get_by_docid
from datatracker import auth
from . import external_sources


log = logging.getLogger(__name__)


shared_context = dict(
    available_serialization_formats=[
        *serializers.registry.keys(),
        'relaton',
    ],
    supported_search_formats=[
        (format, QUERY_FORMAT_LABELS.get(format, format))
        for format in BaseCitationSearchView.supported_query_formats
        if format in QUERY_FORMAT_LABELS
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
    from search query given in ``query``
    and optional ``query_format`` GET parameters.

    - If ``query_format`` is not given, redirects to
      :func:`.browse_citation_by_docid()`.
    - If ``query_format`` is given, redirects to search.
    """

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
    uses :func:`main.query.build_citation_for_docid`
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
        if docid.endswith('.xml'):
            docid = docid[:-len('.xml')]
        citation = build_citation_for_docid(
            docid.strip(),
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
        citation_dict = unpack_dataclasses(citation.dict())
        metrics.gui_bibitem_hits.labels(docid, 'success').inc()
        return render(request, 'browse/citation_details.html', dict(
            data=citation_dict,
            xml2rfc_urls=_get_xml2rfc_urls_safe(citation, request),
            **shared_context,
        ))


def export_citation(request):
    """Calls :func:`main.api.get_by_docid`
    (wrapping it in :func:`datatracker.auth.api`),
    providing appropriate Content-Disposition header and handling errors
    (including authentication errors) by queueing an error-level message
    for the user and redirecting to referer.
    """
    resp = auth.api(get_by_docid)(request)

    if resp.status_code == 200:
        ext = 'xml' if request.GET.get('format') == 'bibxml' else 'json'
        fname = f"{request.GET.get('docid')}.{ext}"
        resp.headers['Content-Disposition'] = f'attachment; filename={fname}'
        return resp

    else:
        # If API failed, redirect back with a message
        message = ""
        if resp.status_code == 403:
            # 403 assumed to mean likely Datatracker token in session expired
            message += "Please re-authenticate and try again. "

        # Inspect API response to extract error message
        message += "Could not export this item, the error was: "
        content = ''.join(resp.content.decode('utf-8'))
        if resp['Content-Type'].startswith('application/json'):
            try:
                err = json.loads(content)['error']
            except (json.JSONDecodeError, KeyError):
                err = content
        else:
            err = content
        message += f"{err}"

        messages.error(request, message)
        return redirect(request.META.get(
            'referer',
            f"{reverse('get_citation_by_docid')}?{request.GET.urlencode()}"))

    return resp


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

def browse_external_reference(request, dataset_id):
    """Allows to view a bibliographic item
    from registered :term:`external source` ``dataset_id``
    by reference passed in request’s GET query parameter ``ref``.
    """
    ref = request.GET.get('ref')

    if ref:
        if source := external_sources.registry.get(dataset_id, None):
            try:
                # external_item = source.get_item(ref.strip())
                item = source.get_item(ref.strip())
                data = unpack_dataclasses(item.dict())
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
                composed = {
                    **data['bibitem'],
                    'primary_docid': ref.strip(),
                    'sources': {
                        dataset_id: data,
                    },
                }
                return render(request, 'browse/citation_details.html', dict(
                    dataset_id=dataset_id,
                    ref=ref,
                    data=composed,
                    xml2rfc_urls=_get_xml2rfc_urls_safe(item.bibitem, request),
                    **shared_context,
                ))
        else:
            log.warn(
                "Unknown external source requested: %s",
                dataset_id)
            messages.error(
                request,
                "Unknown external source “%s”" % dataset_id)
    else:
        messages.error(
            request,
            "Did not receive a reference for external lookup")

    # If we’re here, it must’ve failed
    return HttpResponseRedirect(request.headers.get('referer', '/'))


# Browsing by dataset (semi-internal)
# ===================================

def browse_indexed_reference(request, dataset_id, ref):
    """Allows to view an bibliographic item
    from registered :term:`indexed source` ``dataset_id``
    by reference ``ref``.
    """
    parsed_ref = unquote_plus(ref)

    try:
        indexed_bibitem = unpack_dataclasses(get_indexed_item(
            dataset_id.removeprefix('relaton-data-'),
            parsed_ref,
            strict=False,
        ).dict())

    except RefNotFoundError:
        raise Http404(
            "Requested reference “{}” "
            "could not be found in dataset “{}” "
            "(or external source is unavailable)".format(
                parsed_ref,
                dataset_id))

    else:
        return render(request, 'browse/indexed_bibitem_details.html', dict(
            dataset_id=dataset_id,
            ref=ref,
            data=indexed_bibitem,
            **shared_context,
        ))


class IndexedDatasetCitationListView(ListView):
    model = RefData
    paginate_by = 10
    template_name = 'browse/dataset.html'

    def get(self, request, *args, **kwargs):
        dataset_id = kwargs.get('dataset_id', None)
        if dataset_id not in settings.RELATON_DATASETS:
            raise Http404("No Relaton dataset with such ID")

        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[RefData]:
        return list_refs(self.kwargs['dataset_id'])

    def get_context_data(self, **kwargs):
        ctx = dict(
            **super().get_context_data(**kwargs),
            dataset_id=self.kwargs['dataset_id'],
            **shared_context,
        )
        for item in ctx['object_list']:
            try:
                # XXX: Normalize loose YAML here?
                item.bibitem = BibliographicItem(**item.body)
            except ValidationError:
                pass
        return ctx


def _get_xml2rfc_urls_safe(item: BibliographicItem, request):
    try:
        return xml2rfc_adapters.list_xml2rfc_urls(
            item,
            request,
        )
    except Exception:
        log.exception(
            "Failed to reverse xml2rfc URLs for item %s",
            item.docid)
        return []
