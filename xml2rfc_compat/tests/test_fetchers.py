from django.test import TestCase
from lxml import etree

from main.exceptions import RefNotFoundError
from xml2rfc_compat import fetchers


class XML2RFCFetchersTestCase(TestCase):
    fixtures = ['test_refdata.json']

    def setUp(self):
        self.rfcs_ref = "RFC0001"
        self.misc_ref = "IEEE.802-3.1988"  # or 99983?
        self.test_internet_drafts_ref = "draft-ietf-hip-rfc5201-bis-13"
        self.w3c_ref = "REC-OWL2-SYNTAX-20121211"
        self.threegpp_ref = "TS_25.321_REL-8_8.3.0"
        self.ieee_ref = "IEEE_P2740_D-6.5.2020-08"
        self.iana_ref = "xml-security-uris_security-uris"
        self.rfcsubseries_ref = "STD0029"
        self.nist_ref = "NBS_CRPL-F-A_90"




        # call_command('loaddata', 'xml2rfc/fixtures/test_refdata.json', verbosity=0)

        # repo_url, repo_branch = locate_relaton_source_repo(dataset_id="rfcs")
        # index_dataset("rfcs", f"{get_github_web_data_root(repo_url, repo_branch)}/data", refs=[self.rfcs_ref])
        # found, indexed = indexable_source.index(refs, None, None)

        # registry.get('rfcs').index([], None, None)

        # registry.get('misc').index([], None, None)
        # registry.get('ids').index([self.misc_ref], None, None)
        # registry.get('rfcsubseries').index([self.misc_ref], None, None)
        # registry.get('w3c').index([self.misc_ref], None, None)
        # registry.get('3gpp').index([self.misc_ref], None, None)
        # registry.get('ieee').index([self.misc_ref], None, None)
        # registry.get('iana').index([self.misc_ref], None, None)
        # registry.get('nist').index([self.misc_ref], None, None)

    # def test_rfcs(self):
    #     bibitem = fetchers.rfcs(ref=self.rfcs_ref)
    #     self.assertEqual(bibitem.id, self.rfcs_ref)

    def test_misc(self):
        fetchers.misc(ref=self.misc_ref)

    def test_misc_not_found(self):
        with self.assertRaises(RefNotFoundError):
            fetchers.misc(ref="UNEXISTING_REF")


    def test_internet_drafts(self):
        bibitem = fetchers.internet_drafts(ref=self.internet_drafts_ref)
        # self.assertEqual(bibitem.id, self.internet_drafts_ref)

    def test_w3c(self):
        bibitem = fetchers.w3c(ref=self.w3c_ref)
        # self.assertEqual(bibitem.id, self.w3c_ref)

    def test_threegpp(self):
        bibitem = fetchers.threegpp(ref=self.threegpp_ref)
        # self.assertEqual(bibitem.id, self.threegpp_ref)

    def test_ieee(self):
        bibitem = fetchers.ieee(ref=self.ieee_ref)
        # self.assertEqual(bibitem.id, self.ieee_ref)

    # def test_doi(self):  # todo external
    #     bibitem = fetchers.misc(ref=self.doi_ref)
    #     self.assertEqual(bibitem.id, self.doi_ref)

    def test_iana(self):
        bibitem = fetchers.iana(ref=self.iana_ref)
        # self.assertEqual(bibitem.id, self.iana_ref)

    def test_rfcsubseries(self):
        bibitem = fetchers.rfcsubseries(ref=self.rfcsubseries_ref)
        # self.assertEqual(bibitem.id, self.rfcsubseries_ref)

    def test_nist(self):
        bibitem = fetchers.nist(ref=self.nist_ref)
        # self.assertEqual(bibitem.id, self.nist_ref)


