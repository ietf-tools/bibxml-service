import json
from urllib.parse import unquote_plus

from django.http import HttpResponseBadRequest
from django.views.generic.list import BaseListView
from django.db.models.query import QuerySet

from .models import RefData
from .indexed import RefDataManager
from .indexed import search_refs_json_repr_match, search_refs_relaton_struct


class BaseCitationSearchView(BaseListView):
    model = RefData
    paginate_by = 20
    query_in_path = False
    show_all_by_default = False

    supported_query_formats = (
        'json_repr',
        'json_struct',
    )

    def get(self, request, *args, **kwargs):
        try:
            self.dispatch_parse_query(request, **kwargs)
        except UnsupportedQueryFormat:
            return HttpResponseBadRequest("Unsupported query format")
        except ValueError:
            return HttpResponseBadRequest("Unable to parse query")

        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[RefData]:
        if self.query is not None and self.query_format is not None:
            return self.dispatch_do_query(self.query)
        else:
            if self.show_all_by_default:
                return RefDataManager.all()
            else:
                return RefDataManager.none()

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            query=self.query,
        )

    def dispatch_parse_query(self, request, **kwargs):
        """Parses query and sets up necessary instance attributes
        as a side effect. Guarantees self.query and self.query_format
        will be present.

        Can throw exceptions due to bad input."""

        if not self.query_in_path:
            query = request.GET.get('query', None)
        else:
            query = unquote_plus(kwargs.get('query')).strip()

        query_format = request.GET.get('query_format', 'json_repr')

        if query:
            if query_format.lower() in self.supported_query_formats:
                parser = getattr(
                    self,
                    'parse_%s_query' % query_format.lower(),
                    self.parse_unsupported_query)
            else:
                parser = self.parse_unsupported_query

            self.query = parser(query)
            self.query_format = query_format

        else:
            self.query = None
            self.query_format = None

    def dispatch_do_query(self, query):
        """Handles query.
        Should not throw exceptions arising from bad input."""

        handler = getattr(self, 'handle_%s_query' % self.query_format)
        return handler(query)

    def parse_unsupported_query(self, query_format: str, query: str):
        raise UnsupportedQueryFormat()

    def parse_json_repr_query(self, query: str) -> str:
        return query

    def handle_json_repr_query(self, query: str) -> QuerySet[RefData]:
        return search_refs_json_repr_match(query)

    def parse_json_struct_query(self, query: str) -> dict:
        try:
            struct = json.loads(query)
        except json.JSONDecodeError:
            raise ValueError("Invalid query format")
        else:
            return struct

    def handle_json_struct_query(self, query: dict) -> QuerySet[RefData]:
        return search_refs_relaton_struct(query)


class UnsupportedQueryFormat(ValueError):
    pass
