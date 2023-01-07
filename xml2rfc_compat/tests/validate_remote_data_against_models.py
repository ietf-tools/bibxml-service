# type: ignore
import os
from unittest import TestCase

import yaml
from lxml import etree

from relaton.models import BibliographicItem
from ..serializers import serialize


class DataSourceValidationTestCase(TestCase):

    def setUp(self):
        module_dir = os.path.dirname(__file__)
        file_path = os.path.join(module_dir, "static/schemas/v3.xsd")
        self.xmlschema = etree.XMLSchema(file=file_path)

    def _validate_yaml_data(self, url):
        import requests
        r = requests.get(url)
        yaml_object = yaml.safe_load(r.content)
        bibitem = BibliographicItem(**yaml_object)
        serialized_data = serialize(bibitem)

        self.xmlschema.assertValid(serialized_data)

    def test_validate_rfcs_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-rfcs/main/data/RFC0001.yaml"
        self._validate_yaml_data(url)

    def test_validate_misc_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-misc/main/data/reference.ANSI.T1-102.1987.yaml"
        self._validate_yaml_data(url)

    def test_validate_internet_drafts_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-ids/main/data/draft--pale-email-00.yaml"
        self._validate_yaml_data(url)

    def test_validate_w3c_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-w3c/main/data/2dcontext.yaml"
        self._validate_yaml_data(url)

    def test_validate_threegpp_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-3gpp/main/data/TR_00.01U_UMTS_3.0.0.yaml"
        self._validate_yaml_data(url)

    def test_validate_ieee_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-ieee/main/data/AIEE_11-1943.yaml"
        self._validate_yaml_data(url)

    def test_validate_iana_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-iana/main/data/_6lowpan-parameters.yaml"
        self._validate_yaml_data(url)

    def test_validate_rfcsubseries_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-rfcsubseries/main/data/BCP0003.yaml"
        self._validate_yaml_data(url)

    def test_validate_nist_data(self):
        url = "https://raw.githubusercontent.com/ietf-tools/relaton-data-nist/main/data/NBS_BH_1.yaml"
        self._validate_yaml_data(url)
