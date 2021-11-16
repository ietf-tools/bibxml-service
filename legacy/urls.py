from django.conf import settings
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt

from . import views


_RE_MISC_DATASETS = f"(?P<dataset_name>bibxml2|bibxml\-iso|bibxml\-itu|bibxml\-ansi|bibxml\-fips|bibxml\-ccitt|bibxml\-oasis|bibxml\-pkcs)"


urlpatterns = [
    re_path(
        f"(?P<dataset_name>bibxml)/$", views.index, name="legacy_ietf_rfc_index"
    ),
    re_path(
        f"(?P<dataset_name>bibxml)/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_ietf_rfc_file",
    ),
    re_path(f"{_RE_MISC_DATASETS}/$", views.index, name="legacy_misc_index"),
    re_path(
        f"{_RE_MISC_DATASETS}/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_misc_file",
    ),
    re_path(
        f"(?P<dataset_name>bibxml3|bibxml-ids)/$",
        views.index,
        name="legacy_ietf_draft_index",
    ),
    re_path(
        f"(?P<dataset_name>bibxml3|bibxml-ids)/reference.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_ietf_draft_file",
    ),
    re_path(
        f"(?P<dataset_name>bibxml4|bibxml-w3c)/$",
        views.index,
        name="legacy_w3c_index",
    ),
    re_path(
        f"(?P<dataset_name>bibxml4|bibxml-w3c)/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_w3c_file",
    ),
    re_path(
        f"(?P<dataset_name>bibxml5|bibxml-3gpp)/$",
        views.index,
        name="legacy_3gpp_index",
    ),
    re_path(
        f"(?P<dataset_name>bibxml5|bibxml-3gpp)/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_3gpp_file",
    ),
    re_path(
        f"(?P<dataset_name>bibxml6|bibxml-ieee)/$",
        views.index,
        name="legacy_ieee_index",
    ),
    re_path(
        f"(?P<dataset_name>bibxml6|bibxml-ieee)/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_ieee_file",
    ),
    re_path(
        f"(?P<dataset_name>bibxml7|bibxml-doi)/$",
        views.index,
        name="legacy_doi_index",
    ),
    re_path(
        f"(?P<dataset_name>bibxml7|bibxml-doi)/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_doi_file",
    ),
    re_path(
        f"(?P<dataset_name>bibxml8|bibxml-iana)/$",
        views.index,
        name="legacy_iana_index",
    ),
    re_path(
        f"(?P<dataset_name>bibxml8|bibxml-iana)/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_iana_file",
    ),
    re_path(
        f"(?P<dataset_name>bibxml9|bibxml-rfcsubseries)/$",
        views.index,
        name="legacy_rfcsubseries_index",
    ),
    re_path(
        f"(?P<dataset_name>bibxml9|bibxml-rfcsubseries)/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_rfcsubseries_file",
    ),
    re_path(
        f"(?P<dataset_name>bibxml-nist)/$",
        views.index,
        name="legacy_nist_index",
    ),
    re_path(
        f"(?P<dataset_name>bibxml-nist)/reference\.(?P<doc_name>[A-z0-9\_\-\.\/]+)\.xml$",
        views.bibxml_file,
        name="legacy_nist_file",
    ),
]
