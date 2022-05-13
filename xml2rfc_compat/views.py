"""Generic view functions related to xml2rfc path mapping
and checking xml2rfc path resolution.

Intended to be exposed via private management GUI
and assigned custom templates.
(This module does not supply any templates of its own.)
"""

from typing import Dict, List, Union, Tuple, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError
from pydantic.json import pydantic_encoder
import time
import logging
import json
import simplejson

from django.views.generic import TemplateView
from django.http import HttpResponse, HttpResponseRedirect
from django.http import JsonResponse, Http404, HttpResponseBadRequest
from django.db import transaction
from django.db.models.query import QuerySet
from django.conf import settings
from django.core.cache import cache
from django.contrib import messages

from sources import indexable
from bib_models import BibliographicItem

from .aliases import get_aliases
from .models import ManualPathMap, Xml2rfcItem
from .urls import fetcher_registry, resolve_automatically
from .urls import resolve_manual_map


log = logging.getLogger(__name__)


class DirectoryOverview(TemplateView):
    """
    Renders an overview of top-level directories,
    based on currently indexed :class:`.models.Xml2rfcItem` objects.

    Template will receive ``available_paths``, which is
    a list of :class:`.Xml2rfcDirectoryMeta`.

    Template must be supplied by view user via ``template_name``.
    """

    def get_context_data(self, **kwargs):
        available_paths: Dict[str, Xml2rfcDirectoryMeta] = dict()
        for subpath in Xml2rfcItem.objects.values_list('subpath', flat=True):
            dirname: str = subpath.split('/')[0]
            if dirname not in available_paths:
                prefix = f'{dirname}/'
                fetcher = fetcher_registry.get(dirname)
                if fetcher:
                    available_paths[dirname] = Xml2rfcDirectoryMeta(
                        name=dirname,
                        aliases=get_aliases(dirname),
                        total_count=Xml2rfcItem.objects.
                        filter(subpath__startswith=prefix).
                        count(),
                        manually_mapped_count=ManualPathMap.objects.
                        filter(xml2rfc_subpath__startswith=prefix).
                        count(),
                        fetcher_name=f'{fetcher.__module__}.{fetcher.__name__}'
                        if fetcher else None,
                    )
        return dict(
            available_paths=available_paths.values(),
        )


@dataclass
class Xml2rfcDirectoryMeta:
    """Describes a top-level xml2rfc directory."""

    name: str

    aliases: List[str]
    """Alternative names this directory is known as
    (see :mod:`.aliases`)."""

    total_count: int
    """How many paths are within this directory."""

    manually_mapped_count: int
    """How many paths within this directory
    were manually mapped."""

    fetcher_name: Optional[str]
    """Associated :term:`xml2rfc fetcher` function name."""


class ExploreDirectory(TemplateView):
    """
    Renders an overview of given :term:`xml2rfc-style path`.
    The path can be a subdirectory or a file
    (see :meth:`.get_selection()`).

    If HTTP Accept header is ``application/json``,
    renders a JSON response (see :meth:`.get_json_response()`).

    Otherwise, renders a template
    (see :meth:`get_context_data()` for context).
    Template must be supplied by view user via ``template_name``.
    """

    item_list_cache_seconds = 300
    """How many seconds to cache given directory item listing for."""

    def get(self, request, *args, **kwargs):
        accept = self.request.META['HTTP_ACCEPT']

        if 'application/json' in accept:
            return self.get_json_response(request, *args, **kwargs)

        return super().get(request, *args, **kwargs)

    def get_json_response(self, request, *args, **kwargs):
        """JSON response only returns ``items`` and ``total_items``."""

        self.request = request

        raw_item_idx = request.GET.get('item_at', None)
        item_idx: Union[int, None]
        if raw_item_idx:
            try:
                item_idx = int(raw_item_idx)
            except (ValueError, TypeError):
                return HttpResponseBadRequest("Invalid item index")
        else:
            item_idx = None

        items = self.get_items(**kwargs)
        item_dicts = [dict(path=i.subpath) for i in items]

        data: Dict[str, Any]
        if item_idx is not None:
            try:
                item = item_dicts[item_idx]
            except IndexError:
                return HttpResponse(
                    "Item at specified index not found",
                    status_code=404)
            else:
                data = dict(item=item)
        else:
            data = dict(
                items=item_dicts,
                total_items=len(items),
            )

        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        dirname, selected_item = self.get_selection(**kwargs)

        manual_map_item: Union[BibliographicItem, None]
        automatic_map_item: Union[BibliographicItem, None]

        if selected_item:
            manual_map, manual_map_item, _ = resolve_manual_map(
                selected_item.subpath)

            automatic_map_fetcher = fetcher_registry.get(dirname, None)

            if automatic_map_fetcher:
                _, automatic_map_item, _ = resolve_automatically(
                    selected_item.subpath,
                    selected_item.format_anchor(),
                    automatic_map_fetcher)
            else:
                automatic_map_item = None
        else:
            manual_map = None
            manual_map_item = None
            automatic_map_item = None

        return dict(
            selected_item=selected_item,
            selected_item_map=dict(
                manual=dict(
                    config=manual_map,
                    item=manual_map_item,
                ),
                automatic_item=automatic_map_item,
                effective_item=manual_map_item or automatic_map_item,
            ),
            items=self.get_items(**kwargs),
            dirname=dirname,
            global_prefix=settings.XML2RFC_PATH_PREFIX,
            cache_key=self.get_cache_key(dirname),
        )

    def get_cache_key(self, dirname) -> str:
        """
        A cache key that is guaranteed to change if any mapped path changes,
        or if the number of indexed xml2rfc paths is different.
        """
        no_cache = self.request.GET.get('bypass_cache', None)
        if no_cache:
            return str(time.time())
        else:
            indexed_count = indexable.registry['xml2rfc'].count_indexed()
            mapped_paths = frozenset([
                f'{m.xml2rfc_subpath}:{m.docid}'
                for m in ManualPathMap.objects.all().order_by('xml2rfc_subpath')
            ])
            return json.dumps({
                'total_indexed': indexed_count,
                'map_hash': hash(mapped_paths),
                'dirname': dirname,
            })

    def get_selection(self, **kwargs) -> Tuple[str, Union[Xml2rfcItem, None]]:
        """
        Returns a 2-tuple
        (selected dirname: str, selected item subpath: str or None).

        Obtains them using ``subpath`` passed in via URL kwargs.
        """
        if 'subpath' not in kwargs:
            raise RuntimeError("Subpath must be specified in path kwargs.")

        subpath = kwargs['subpath']

        if '/' in subpath:
            dirname = subpath.split('/')[0]
            try:
                selected_item = Xml2rfcItem.objects.get(subpath=subpath)
            except Xml2rfcItem.DoesNotExist:
                raise Http404("Unable to locate selected item")
        else:
            dirname = subpath
            selected_item = None

        return dirname, selected_item

    def get_items(self, **kwargs) -> QuerySet[Xml2rfcItem]:
        """
        Lists all items within currently selected dirname.
        Caches the result by :attr:`.item_list_cache_seconds`.
        """
        dirname, _ = self.get_selection(**kwargs)

        result = cache.get_or_set(
            self.get_cache_key(dirname),
            lambda: Xml2rfcItem.objects.filter(
                subpath__startswith='%s/' % dirname,
            ).order_by('subpath'),
            self.item_list_cache_seconds)
        return result


def edit_manual_map(request, subpath):
    docid = request.POST.get('docid')
    if docid:
        ManualPathMap.objects.update_or_create(
            xml2rfc_subpath=subpath,
            defaults=dict(
                docid=docid,
            ),
        )
    else:
        messages.error(
            request,
            "Cannot map <code class=\"font-monospace\">%s</code>: "
            "document identifier was not specified"
            % subpath)

    return HttpResponseRedirect(request.headers.get('referer', '/management/'))


def delete_manual_map(request, subpath):
    try:
        ManualPathMap.objects.get(
            xml2rfc_subpath=subpath,
        ).delete()
    except ManualPathMap.DoesNotExist:
        messages.info(
            request,
            "No manual map was found "
            "for <code class=\"font-monospace\">%s</code>, "
            "so no action was performed."
            % subpath)

    return HttpResponseRedirect(request.headers.get('referer', '/management/'))


class SerializedPathMap(BaseModel):
    """
    Representation of :class:`xml2rfc_compat.models.ManualPathMap`
    for mappings exported to JSON.
    """

    path: str
    """xml2rfc subpath, relative to ``/public/rfc/`` root.

    It **must** contain unaliased directory name first,
    such as ``bibxml2``."""

    docid: str
    """``docid.id`` mapped to given path."""


def export_manual_map(request):
    mappings = [
        dict(path=i.xml2rfc_subpath, docid=i.docid)
        for i in ManualPathMap.objects.all().order_by('xml2rfc_subpath')
    ]
    return JsonResponse(
        {'mappings': mappings},
        headers={
            'Content-Disposition':
                'attachment; filename=bibxml-service-xml2rfc-path-map.json',
        },
        json_dumps_params=dict(indent=4))


def import_manual_map(request):
    """
    Handles upload of a JSON file with manual mappings.
    JSON file must contain a list of :class:`.SerializedPathMap` items.
    """
    json_file = request.FILES.get('map_json', None)

    if json_file:
        try:
            data = simplejson.loads(json_file.read())
            mappings = (
                SerializedPathMap.parse_obj(item)
                for item in data['mappings']
            )
        except (simplejson.JSONDecodeError, KeyError):
            messages.error(
                request,
                "Error decoding xml2rfc map JSON")
        except ValidationError:
            messages.error(
                request,
                "xml2rfc map contains invalid data")
        except RuntimeError:
            messages.error(
                request,
                "Unknown error reading the uploaded xml2rfc map")
            log.exception("Error reading imported xml2rfc map")

        else:
            clear = request.POST.get('clear', False)

            total_read = 0
            with transaction.atomic():
                if clear:
                    ManualPathMap.objects.all().delete()
                    for item in mappings:
                        ManualPathMap.objects.update_or_create(
                            xml2rfc_subpath=item.path,
                            defaults=dict(docid=item.docid),
                        )
                        total_read += 1
                else:
                    for item in mappings:
                        ManualPathMap.objects.get_or_create(
                            xml2rfc_subpath=item.path,
                            defaults=dict(docid=item.docid),
                        )
                        total_read += 1
            messages.success(
                request,
                f"Created or updated {total_read} xml2rfc path mappings")
    else:
        messages.error(
            request,
            "Did not receive a file to load xml2rfc map from")

    return HttpResponseRedirect(request.headers.get('referer', '/management/'))
