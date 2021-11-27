import json
from typing import Union, Callable
from urllib.parse import unquote_plus

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

    def get(self, request, *args, **kwargs):
        if not self.query_in_path:
            raw_query = request.GET.get('query', None)
        else:
            raw_query = kwargs.get('query')

        self.query_func, self.query = self.parse_query(
            raw_query,
            request.GET.get('query_format', 'json_repr'))

        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[RefData]:
        if self.query_func is not None and self.query is not None:
            return self.query_func(self.query)
        else:
            if self.show_all_by_default:
                return RefDataManager.all()
            else:
                return RefDataManager.none()

    def parse_query(
        self, raw_query: Union[str, None],
        mechanism: str) -> Union[tuple[Callable[[str],
                                                QuerySet[RefData]],
                                       str],
                                 tuple[Callable[[Union[dict, list]],
                                                QuerySet[RefData]],
                                       Union[dict, list]],
                                 tuple[None, None]]:

        # Somebody help reign in flake8…

        if mechanism not in ['json_repr', 'json_struct']:
            raise ValueError("Invalid query mechanism")

        if raw_query:
            prepared_query = unquote_plus(raw_query).strip()

            if prepared_query:
                if mechanism == 'json_repr':
                    return (search_refs_json_repr_match, prepared_query)
                else:
                    try:
                        struct = json.loads(prepared_query)
                    except json.JSONDecodeError:
                        raise ValueError("Invalid query format")
                    else:
                        return (search_refs_relaton_struct, struct)

        return (None, None)
