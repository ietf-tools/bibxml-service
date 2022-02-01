import logging
import functools
from typing import Dict, Callable, List
import re
from urllib.parse import unquote_plus

from django.urls import re_path
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from django.http import HttpResponse, JsonResponse, HttpResponseNotFound
from django.http import HttpResponseServerError
from django.conf import settings
from django.db.models.query import Q

from pydantic import ValidationError

from common.util import as_list
from bib_models.models import BibliographicItem
from bib_models.to_xml import to_xml_string
from prometheus import metrics
from .indexed import search_refs_relaton_field
from .indexed import build_citation_for_docid
from .external import get_doi_ref as _get_doi_ref
from .exceptions import RefNotFoundError
from .indexed import get_indexed_ref_by_query


log = logging.getLogger(__name__)


def make_xml2rfc_path_pattern(
        dirnames: List[str],
        fetcher_func: Callable[[str], BibliographicItem]):
    """Constructs Django URL resolver patterns
    for a given list of dirnames.

    Each path is in the shape of
    ``<dirname>/[_]reference.<anchor>.xml``,
    and constructed view delegates bibliographic item
    retrieval to provided fetcher function.

    Fetcher function is passed the ``anchor`` kwarg,
    for which it must return a :class:`BibliographicData` instance,
    and is expected to raise either ``RefNotFoundError``
    or pydantic’s ``ValidationError``.
    """
    return [
        re_path(
            r'(?P<xml2rfc_subpath>%s/'
            r'_?reference\.(?P<anchor>[-A-Za-z0-9./_]+)\.xml'
            r')$'
            % dirname,
            never_cache(require_safe(
                make_xml2rfc_path_handler(fetcher_func),
            )),
            name='xml2rfc_%s' % dirname)
        for dirname in dirnames
    ]


def make_xml2rfc_path_handler(fetcher_func: Callable[
    [str], BibliographicItem
]):
    """Creates a view function, given a fetcher function.

    Fetcher function will receive a cleaned xml2rfc filename
    (just the anchor, without the “reference.” or “_reference.” prefix
    or the .xml extension)
    and must return a :class:`BibliographicItem` instance.

    The automatically created view function handles filename
    cleanup, constructing a :class:`BibliographicItem`
    and converting it to XML string with proper anchor tag supplied.
    """

    @functools.wraps(fetcher_func)
    def handle_xml2rfc_path(request, xml2rfc_subpath: str, anchor: str):
        resp: HttpResponse
        outcome: str

        try:
            item = fetcher_func(anchor)
        except RefNotFoundError:
            log.error("Item for xml2rfc path not found: %s", xml2rfc_subpath)
            outcome = 'not_found_no_fallback'
            resp = HttpResponseNotFound(
                "Item for xml2rfc path not found: %s" % xml2rfc_subpath)
        except ValidationError:
            log.exception(
                "Item found for xml2rfc path did not validate: %s",
                xml2rfc_subpath)
            outcome = 'validation_error'
            resp = HttpResponseServerError(
                "Error constructing bibliographic item for given xml2rfc path")
        else:
            outcome = 'success'
            resp = HttpResponse(
                to_xml_string(item, anchor=anchor),
                content_type="application/xml",
                charset="utf-8")

        metrics.xml2rfc_api_bibitem_hits.labels(xml2rfc_subpath, outcome).inc()
        return resp

    return handle_xml2rfc_path


# Old method 2 (fuzzy)
# ====================

def get_ref_by_legacy_path(request, legacy_dataset_name, legacy_reference):
    try:
        bibxml_repr = get_xml2rfc_ref_v2(legacy_dataset_name, legacy_reference)

    except BadDatasetNameError:
        return JsonResponse({
            "error":
                "Unable to get XML for '{}' in dataset {} "
                "(unknown dataset name)".
                format(legacy_reference, legacy_dataset_name),
        }, status=400)

    except RefNotFoundError:
        return JsonResponse({
            "error":
                "Unable to get XML for '{}' "
                "in legacy dataset {}".
                format(legacy_reference, legacy_dataset_name),
        }, status=404)

    except ValidationError:
        return JsonResponse({
            "error":
                "Unable to get XML for '{}' "
                "in legacy dataset {} "
                "(source bibliographic item is malformed)".
                format(legacy_reference, legacy_dataset_name),
        }, status=500)

    except ValueError:
        return JsonResponse({
            "error":
                "Unable to get XML for '{}' "
                "in legacy dataset {} "
                "(source bibliographic item cannot be converted per RFC 7991)".
                format(legacy_reference, legacy_dataset_name),
        }, status=500)

    else:
        return HttpResponse(
            bibxml_repr,
            content_type="application/xml",
            charset="utf-8")


def get_xml2rfc_ref_v2(legacy_dataset_name: str, legacy_reference: str) -> str:
    ref_without_prefix = (
        legacy_reference.
        replace('reference.', '').
        replace('_reference.', ''))

    rough_docid = ref_without_prefix.replace('.', ' ').replace('_', ' ')
    basic_criteria = {
        'docid[*]': '@.id like_regex "(?i)%s"' % re.escape(rough_docid),
    }
    ds_name = (
        getattr(settings, 'XML2RFC_DIR_ALIASES', {}).
        get(legacy_dataset_name, legacy_dataset_name)
    )
    extra_criteria: Callable[[str], Dict[str, str]] = (
        getattr(settings, 'XML2RFC_DIR_TO_DOCID_TYPE', {}).
        get(ds_name, lambda ref_without_prefix, criteria: criteria)
    )

    refs = search_refs_relaton_field(
        extra_criteria(ref_without_prefix, basic_criteria),
        limit=10,
        exact=True,
    )
    if len(refs) > 0:
        docid = as_list(refs[0].body['docid'])[0]
        bibitem = build_citation_for_docid(docid['id'], docid['type'])
        return to_xml_string(bibitem, anchor=ref_without_prefix)
    else:
        raise RefNotFoundError(
            "Unable to locate bibliographic item",
            rough_docid)


# Old method (by ref)
# ===================

DEFAULT_LEGACY_REF_PREFIX = 'reference.'

DEFAULT_LEGACY_REF_FORMATTER = (
    lambda legacy_ref:
    legacy_ref[len(DEFAULT_LEGACY_REF_PREFIX):])

DEFAULT_LEGACY_QUERY_BUILDER = (
    lambda legacy_ref:
    Q(ref__iexact=DEFAULT_LEGACY_REF_FORMATTER(legacy_ref)))


def get_xml2rfc_ref_v1(legacy_dataset_name: str, legacy_reference: str) -> str:
    """Retrieves XML string for given xml2rfc-style reference
    using the ``LEGACY_DATASETS``-based approach.

    :raises RefNotFoundError: bubbles up if either the item or its xml repr
                              couldn’t be found
    :raises ValueError: given ``legacy_dataset_name`` does not have an entry
                        in ``LEGACY_DATASETS``.
    """

    legacy_ds_id_or_config = settings.LEGACY_DATASETS.get(
        legacy_dataset_name.lower(),
        None)

    if legacy_ds_id_or_config:

        if hasattr(legacy_ds_id_or_config, 'get'):
            dataset_id = legacy_ds_id_or_config['dataset_id']
            path_prefix = legacy_ds_id_or_config.get(
                'path_prefix',
                DEFAULT_LEGACY_REF_PREFIX)
            ref_formatter = (
                legacy_ds_id_or_config.get('ref_formatter', None) or
                (lambda legacy_ref: legacy_reference[len(path_prefix):]))
            query_builder = (
                legacy_ds_id_or_config.get('query_builder', None) or
                (lambda legacy_ref:
                    Q(ref__iexact=ref_formatter(legacy_ref))))
        else:
            dataset_id = legacy_ds_id_or_config
            ref_formatter = DEFAULT_LEGACY_REF_FORMATTER
            query_builder = DEFAULT_LEGACY_QUERY_BUILDER

        parsed_legacy_ref = unquote_plus(legacy_reference)
        parsed_ref = ref_formatter(parsed_legacy_ref)

        if dataset_id == 'doi':
            return _get_doi_ref(parsed_ref, 'bibxml')
        else:
            return get_indexed_ref_by_query(
                dataset_id,
                query_builder(parsed_legacy_ref),
                'bibxml')

    else:
        raise BadDatasetNameError("Legacy dataset is unknown")


class BadDatasetNameError(ValueError):
    pass
