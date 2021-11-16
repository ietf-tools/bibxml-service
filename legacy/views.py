# from django.shortcuts import render

from django.http import HttpResponse


from django.conf import settings

import re


DATASET_MAP = {
    **dict.fromkeys(
        ["bibxml"],
        {
            "name": "ietf-rfcs",
            "re_file": re.compile("^RFC\.(?P<name>[A-z0-9\_\-\.\/]+)$"),
        },
    ),
    **dict.fromkeys(
        [
            "bibxml2",
            "bibxml-iso",
            "bibxml-itu",
            "bibxml-ansi",
            "bibxml-fips",
            "bibxml-ccitt",
            "bibxml-oasis",
            "bibxml-pkcs",
        ],
        {
            "name": "misc",
            "re_file": re.compile(
                "^(?P<type>W3C|ISO|ITU|ANSI|FIPS|CCITT|IEEE|OASIS|PKCS)\.(?P<name>[A-z0-9\_\-\.\/]+)$"
            ),
        },
    ),
    **dict.fromkeys(
        ["bibxml3", "bibxml-ids"],
        {
            "name": "ietf-draft",
            "re_file": re.compile("^I-D\.(?P<name>[A-z0-9\_\-\.\/]+)$"),
        },
    ),
    **dict.fromkeys(
        ["bibxml4", "bibxml-w3c"],
        {
            "name": "w3c",
            "re_file": re.compile("^W3C\.(?P<name>[A-z0-9\_\-\.\/]+)$"),
        },
    ),
    **dict.fromkeys(
        ["bibxml5", "bibxml-3gpp"],
        {
            "name": "3gpp",
            "re_file": re.compile(
                "^(?P<type>3GPP|SDO\-3GPP)\.(?P<name>[A-z0-9\_\-\.\/]+)$"
            ),
        },
    ),
    **dict.fromkeys(
        ["bibxml6", "bibxml-ieee"],
        {
            "name": "ieee",
            "re_file": re.compile("^IEEE\.(?P<name>[A-z0-9\_\-\.\/]+)$"),
        },
    ),
    **dict.fromkeys(
        ["bibxml7", "bibxml-doi"],
        {
            "name": "doi",
            "re_file": re.compile("^DOI\.(?P<name>[A-z0-9\_\-\.\/]+)$"),
        },
    ),
    **dict.fromkeys(
        ["bibxml8", "bibxml-iana"],
        {
            "name": "iana",
            "re_file": re.compile("^IANA\.(?P<name>[A-z0-9\_\-\.\/]+)$"),
        },
    ),
    **dict.fromkeys(
        ["bibxml9", "bibxml-rfcsubseries"],
        {
            "name": "ietf-rfcsubseries",
            "re_file": re.compile(
                "^(?P<type>BCP|FYI|STD)\.(?P<name>[A-z0-9\_\-\.\/]+)$"
            ),
        },
    ),
    **dict.fromkeys(
        ["bibxml-nist"],
        {
            "name": "nist",
            "re_file": re.compile("^NIST\.(?P<name>[A-z0-9\_\-\.\/]+)$"),
        },
    ),
}


def index(request, dataset_name):
    return HttpResponse(
        "There is list of legacy  files of '%s' dataset" % dataset_name
    )


def bibxml_file(request, dataset_name, doc_name):

    dataset = DATASET_MAP.get(dataset_name, None)
    if dataset:
        found = dataset["re_file"].match(doc_name)
        if found:
            found_dict = found.groupdict()
            doc_suffix = found_dict.get("name")
            subset_name = found_dict.get("type", dataset["name"])

            return HttpResponse(
                "This is content of file 'reference.%s.xml' of '%s' dataset. Doc name: '%s', type: '%s'."
                % (doc_name, dataset["name"], doc_suffix, subset_name)
            )
        else:
            return HttpResponse("File 'reference.%s.xml' not found" % doc_name)
    else:
        return HttpResponse("Unknown dataset: %s" % dataset_name)
