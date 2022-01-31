import re
import json
from typing import Any, List, Callable, Union
from urllib.parse import unquote_plus

from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.views.generic.list import BaseListView
from django.db.models.query import QuerySet
from django.conf import settings
from django.core.cache import cache
from django.http import Http404
from django.contrib import messages

from .types import CompositeSourcedBibliographicItem
from .models import RefData
from .indexed import build_search_results
from .indexed import search_refs_relaton_struct
from .indexed import search_refs_relaton_field
from .indexed import query_suppressing_user_input_error


QUERY_FORMAT_LABELS = {
    'json_struct': "JSON containment",
    'docid_regex': "docid substring",
    'json_path': "JSON path",
    'websearch': "web search",
}


jsonpath_re = [
    re.compile(r'^\$\.'),  # Query a la $.docid[*]… is a @@ style query
]
"""If any of these expression matches,
user-provided search string can be assumed to be
a PostgreSQL’s ``@@`` JSON path style query
against the whole bibliographic item."""

is_jsonpath: Callable[[str], bool] = (
    lambda query: any(
        exp.search(query) is not None
        for exp in jsonpath_re)
)
"""Returns True if given query looks like a JSON path query."""


websearch_re = [
    re.compile(r'"\S+"'),  # Quoted substring
    re.compile(r'\s-\S'),  # Token prepended with a - (negation)
    re.compile(r'\bOR\b'),  # OR operator
]
"""If any of these expression matches,
user-provided search string can be assumed to be
a PostgreSQL web search style query."""

is_websearch: Callable[[str], bool] = (
    lambda query: not is_jsonpath(query) and any(
        exp.search(query) is not None
        for exp in websearch_re)
)
"""Returns True if given query looks like a web search style query."""


class BaseCitationSearchView(BaseListView):
    """Generic view that handles citation search.

    Intended to be usable for both template-based GUI and API views."""

    # model = RefData
    paginate_by = 10

    limit_to = getattr(settings, 'DEFAULT_SEARCH_RESULT_LIMIT', 100)
    """Hard limit for found item count.

    If the user hits this limit, they are expected to provide
    a more precise query."""

    query_in_path = False
    """Whether query will appear as path component named ``query``
    (URLs must be configured appropriately).

    Otherwise, it’s expected to be supplied
    as a GET parameter named ``query``."""

    supported_query_formats = (
        'docid_regex',
        'json_struct',
        'json_path',
        'websearch',
    )
    """Allowed values of query format in request.

    Order of supported query formats matters when fallback is allowed,
    then it’s better to ordered them fast and precise
    to slow and imprecise."""

    query_format = None
    """Query format obtained from request,
    one of :attr:`supported_query_formats`."""

    query_format_allow_fallback = None
    """If True, and given query is unsuccessful, will try the next format.
    Can be overridden with ``allow_format_callback`` GET parameter."""

    query = None
    """Deserialized query, parsed from request."""

    show_all_by_default = False
    """Whether to show all items if query is not specified.

    Still subject to ``limit_to``."""

    base_urlpattern_name: Union[str, None] = None
    """Base URL pattern name for this view."""

    result_cache_seconds = getattr(settings, 'SEARCH_CACHE_SECONDS', 3600)
    """How long to cache search results for. Results are cached as a list
    is constructed from query and query format. Default is one hour."""

    metric_counter = None
    """A Prometheus Counter instance accepting two labels,
    ``query_format`` and ``got_results``.
    """

    def get(self, request, *args, **kwargs):
        self.is_gui = hasattr(self, 'template_name')

        if not self.query_in_path:
            self.raw_query = request.GET.get('query', None)
        else:
            self.raw_query = unquote_plus(kwargs.get('query', '')).strip()

        if not self.raw_query and self.is_gui:
            messages.warning(
                request,
                "Search query was not provided.")
            return HttpResponseRedirect(request.headers.get('referer', '/'))

        self.query_format_allow_fallback = bool(request.GET.get(
            'allow_format_fallback',
            self.query_format_allow_fallback or False))

        query_format = request.GET.get(
            'query_format',
            self.supported_query_formats[0])

        try:
            self.dispatch_parse_query(
                request,
                query=self.raw_query,
                query_format=query_format,
                suppress_errors=self.query_format_allow_fallback,
                **kwargs)

        except UnsupportedQueryFormat:
            if self.is_gui:
                messages.warning(
                    request,
                    "Search query format is unsupported.")
            else:
                return HttpResponseBadRequest("Unsupported query format")

        except ValueError:
            if self.is_gui:
                messages.warning(
                    request,
                    "Unable to parse search query.")
            else:
                return HttpResponseBadRequest("Unable to parse query")

        return super().get(request, *args, **kwargs)

    def paginate_queryset(self, queryset, page_size):
        try:
            return super().paginate_queryset(queryset, page_size)
        except Http404:
            if self.is_gui:
                messages.warning(
                    self.request,
                    "Requested page number doesn’t exist in this search, "
                    "or at least not anymore. Showing first page instead.")
                paginator = self.get_paginator(
                    queryset, page_size, orphans=self.get_paginate_orphans(),
                    allow_empty_first_page=True)
                page = paginator.page(1)
                return (
                    paginator,
                    page,
                    page.object_list,
                    page.has_other_pages(),
                )
            else:
                raise

    def get_queryset(self) -> List[CompositeSourcedBibliographicItem]:
        """Returns a ``QuerySet`` of ``RefData`` objects.

        If query is present, delegates to :meth:`dispatch_handle_query`,
        otherwise behavior depends on :attr:`show_all_by_default`."""

        if self.query is not None and self.query_format is not None:
            result_getter = (lambda: build_search_results(
                self.dispatch_handle_query(self.query)))

            if self.request.GET.get('bypass_cache'):
                return result_getter()
            else:
                return cache.get_or_set(
                    json.dumps({
                        'query': self.query,
                        'query_format': self.query_format,
                        'limit': self.limit_to,
                        'show_all': self.show_all_by_default,
                    }),
                    result_getter,
                    self.result_cache_seconds)
        else:
            return []

    def get_search_query_context_data(self, **kwargs):
        query_format_label = QUERY_FORMAT_LABELS.get(
            self.query_format,
            self.query_format,
        ) if self.query_format else None

        return dict(
            result_cap=self.limit_to,
            cache_ttl=self.result_cache_seconds,
            query=self.query,
            query_format=self.query_format,
            query_format_label=query_format_label,
        )

    def get_context_data(self, **kwargs):
        """In addition to parent implementation,
        provides search-related variables.

        As a side-effect, queries a message regarding query format.
        """

        ctx = dict(
            **super().get_context_data(**kwargs),
            **self.get_search_query_context_data(),
        )

        query_format_label = ctx['query_format_label']

        orig_format = self.request.GET.get('query_format')
        if self.query_format and orig_format != self.query_format:
            if orig_format:
                msg = (
                    "Requested query did not yield results; "
                    f"treating query as “{query_format_label}”."
                )
            else:
                msg = (
                    "No search method was given; "
                    f"treating query as “{query_format_label}”."
                )
            messages.info(self.request, msg)

        return ctx

    def get_next_query_format(self, query_format) -> Union[str, None]:
        """Given ``query_format``, finds the next supported format in list.

        :returns: The next supported format.

                  - If ``query_format`` is invalid,
                    returns *the first* supported format.
                  - If no more formats are available,
                    returns None.

        :rtype: None or str
        """
        idx = self.supported_query_formats.index(query_format)
        try:
            return self.supported_query_formats[idx + 1]
        except ValueError:
            # Bad format, try from the beginning
            return self.supported_query_formats[0]
        except IndexError:
            # No more formats to try
            return None

    def dispatch_parse_query(self,
                             request,
                             query=None,
                             query_format=None,
                             suppress_errors=False,
                             **kwargs):
        """Parses query and guarantees :attr:`query` and :attr:`query_format`
        are present, although they can be ``None``.

        Delegates parsing to ``parse_{query-format}_query()`` method.

        Throws exceptions due to bad input,
        unless ``suppress_errors`` is given.

        If :attr:`query_format_allow_fallback` is ``True``,
        recurses via :meth:`get_next_query_format()` instead of raising,
        but ``suppress_errors`` is still effective at final pass.
        """

        if query:
            if query_format.lower() in self.supported_query_formats:
                parser = getattr(
                    self,
                    'parse_%s_query' % query_format.lower(),
                    self.parse_unsupported_query)
            else:
                parser = self.parse_unsupported_query

            try:
                self.query = parser(query)
            except (UnsupportedQueryFormat, ValueError) as parse_error:
                if self.query_format_allow_fallback:
                    next_format = self.get_next_query_format(query_format)
                    if next_format:
                        return self.dispatch_parse_query(
                            request,
                            query,
                            query_format=next_format,
                            suppress_errors=suppress_errors)
                if suppress_errors:
                    self.query_format = None
                else:
                    raise parse_error
            else:
                self.query_format = query_format

        else:
            self.query = None
            self.query_format = None

    def dispatch_handle_query(self, query) \
            -> QuerySet[RefData]:
        """Handles query by delegating
        to ``handle_{query-format}_query()`` method.

        Forces evaluation of returned queryset of ``RefData`` instances.

        Exceptions arising from

        Is not expected to throw exceptions arising from bad input.

        If :attr:`query_format_allow_fallback` is ``True``,
        an error or empty queryset obtained when
        """

        handler = getattr(self, 'handle_%s_query' % self.query_format)

        qs = query_suppressing_user_input_error(lambda: handler(query))

        input_error = qs is None
        found_something = qs is not None and len(qs) > 0
        found_too_many = len(qs) >= self.limit_to

        if input_error:
            if self.show_all_by_default:
                qs = RefData.objects.all()[:self.limit_to]
            else:
                qs = RefData.objects.none()

        if not found_something and self.query_format_allow_fallback:
            next_format = self.get_next_query_format(self.query_format)
            if next_format:
                self.dispatch_parse_query(
                    self.request,
                    query=self.raw_query,
                    query_format=next_format,
                    suppress_errors=True)
                return self.dispatch_handle_query(self.query)

        elif not found_something:
            msg = (
                "Query may have used incorrect syntax."
                if input_error
                else "No bibliographic items were found matching the query.")
            can_try_other_formats = (
                self.supported_query_formats.index(self.query_format)
                < (len(self.supported_query_formats) - 1)
            )
            if not self.query_format_allow_fallback and can_try_other_formats:
                querydict = self.request.GET.copy()
                querydict['allow_format_fallback'] = True
                try:
                    querydict.pop('query_format')
                except KeyError:
                    pass
                else:
                    url = '{}?{}'.format(
                        reverse('search_citations'),
                        querydict.urlencode(),
                    )
                    msg = (
                        f"{msg} "
                        f"You may <a class=\"underline\" href=\"{url}\">"
                        "retry the same query"
                        "</a> "
                        "trying all available search methods."
                    )
            messages.error(self.request, msg)

        if self.metric_counter:
            if found_too_many:
                got_results = 'too_many'
            elif found_something:
                got_results = 'yes'
            else:
                got_results = 'no'
            self.metric_counter.labels(
                self.query_format,
                got_results,
            ).inc()

        return qs

    def parse_unsupported_query(self, query: str):
        raise UnsupportedQueryFormat()

    # Supported query formats
    # =======================

    # Parsers

    def parse_docid_regex_query(self, query: str) -> str:
        if not is_websearch(query) and not is_jsonpath(query):
            return query
        else:
            raise ValueError("Query does not look like a regex query")

    def parse_json_struct_query(self, query: str) -> dict[str, Any]:
        try:
            struct = json.loads(query)
        except json.JSONDecodeError:
            raise ValueError("Invalid query format (not a JSON structure)")
        else:
            return struct

    def parse_json_path_query(self, query: str) -> str:
        return query

    def parse_websearch_query(self, query: str) -> str:
        return query

    # Handlers

    def handle_docid_regex_query(self, query: str) -> QuerySet[RefData]:
        return search_refs_relaton_field(
            {
                'docid[*]': '@.id like_regex "(?i)%s"' % re.escape(query),
            },
            limit=self.limit_to,
            exact=True,
        )

    def handle_json_struct_query(
            self,
            query: dict[str, Any]) -> QuerySet[RefData]:
        return search_refs_relaton_struct(
            query,
            limit=self.limit_to)

    def handle_json_path_query(
            self,
            query: str) -> QuerySet[RefData]:
        return search_refs_relaton_field(
            {'': query},
            limit=self.limit_to,
            exact=True,
        )

    def handle_websearch_query(self, query: str) -> QuerySet[RefData]:
        return search_refs_relaton_field(
            {'': query},
            limit=self.limit_to,
        )


class UnsupportedQueryFormat(ValueError):
    """Specified query format is not supported."""
    pass
