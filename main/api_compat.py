from typing import Dict, Callable
import re
from urllib.parse import unquote_plus

from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.db.models.query import Q

from pydantic import ValidationError

from common.util import as_list
from bib_models.to_xml import to_xml_string
from .indexed import search_refs_relaton_field
from .indexed import build_citation_for_docid
from .external import get_doi_ref as _get_doi_ref
from .exceptions import RefNotFoundError
from .indexed import get_indexed_ref_by_query


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


# New method (fuzzy)
# ==================

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
