import textwrap

import yaml

from django.http import HttpResponseBadRequest
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from django.shortcuts import render

from bib_models.models import BibliographicItem
from main.indexed import list_doctypes
from main.api import CitationSearchResultListView


def openapi_spec(request):
    """Serves machine-readable spec for main API."""

    schemas = BibliographicItem.schema(
        ref_template='#/components/schemas/{model}',
    )['definitions']
    bibitem_objects = textwrap.indent(
        yaml.dump(schemas),
        '    ')

    search_formats = CitationSearchResultListView.supported_query_formats

    return render(request, 'openapi.yaml', dict(
        known_doctypes=list_doctypes(),
        known_dataset_ids=list(
            getattr(settings, 'KNOWN_DATASETS', [])),
        pre_indented_bibliographic_item_definitions=bibitem_objects,
        supported_search_query_formats=search_formats,
    ), content_type='text/x-yaml')


def legacy_openapi_spec(request):
    """Serves machine-readable spec for compatibility/legacy API."""
    return render(request, 'openapi-legacy.yaml', dict(
        legacy_dataset_ids=list(
            getattr(settings, 'LEGACY_DATASETS', {}).keys()),
    ), content_type='text/x-yaml')


def readable_openapi_spec(request, spec: str):
    """Serves human-readable page for given OpenAPI spec
    (provided as a valid arg-free urlpattern name)."""

    try:
        path = reverse(spec)
    except NoReverseMatch:
        return HttpResponseBadRequest("Invalid spec")
    else:
        return render(request, 'human_readable_openapi_spec.html', dict(
            spec_path=path,
        ))


def readable_openapi_spec_main(request):
    """A shortut for :func:`readable_openapi_spec`
    with pre-filled spec ID referencing main OpenAPI spec."""
    return readable_openapi_spec(request, 'openapi_spec_main')
