"""Prometheus recommends to be thoughtful about which metrics are tracked,
so we instantiate all of them in a single module
rather than in corresponding modules.
"""

# Empty docstrings are workarounds
# to include these self-explanatory metrics in Sphinx autodoc.

from prometheus_client import Counter


_prefix_ = 'bibxml_service_'


gui_home_page_hits = Counter(
    f'{_prefix_}gui_home_page_hits_total',
    "Home page hits",
)
""""""


gui_search_hits = Counter(
    f'{_prefix_}gui_search_hits_total',
    "Searches via GUI",
    ['query_format', 'got_results'],
    # got_results should be 'no', 'yes', 'too_many'
)
""""""


gui_bibitem_hits = Counter(
    f'{_prefix_}gui_bibitem_hits_total',
    "Bibitem accesses via GUI",
    ['document_id', 'outcome'],
    # outcome should be either success or not_found
)
""""""


api_search_hits = Counter(
    f'{_prefix_}api_search_hits_total',
    "Searches via API",
    ['query_format', 'got_results'],
    # got_results should be 'no', 'yes', 'too_many'
)
""""""


api_bibitem_hits = Counter(
    f'{_prefix_}api_bibitem_hits_total',
    "Bibitem accesses via API",
    ['document_id', 'outcome', 'format'],
    # outcome should be a limited enum,
    # e.g. success/not_found/validation_error/serialization_error
)
""""""


xml2rfc_api_bibitem_hits = Counter(
    f'{_prefix_}xml2rfc_api_bibitem_hits_total',
    "Bibitem accesses via xml2rfc tools style API",
    ['path', 'outcome'],
    # outcome should be either success, fallback or not_found
)
""""""
