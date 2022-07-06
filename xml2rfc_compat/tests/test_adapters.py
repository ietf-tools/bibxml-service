from django.test import TestCase

from bib_models import BibliographicItem
from bibxml.settings import XML2RFC_PATH_PREFIX
from bibxml.xml2rfc_adapters import RfcAdapter, MiscAdapter, InternetDraftsAdapter, W3cAdapter, ThreeGPPPAdapter, \
    IeeeAdapter, IanaAdapter, RfcSubseriesAdapter
from main.exceptions import RefNotFoundError


class XML2RFCAdaptersTestCase(TestCase):
    fixtures = ['test_refdata.json']

    def setUp(self):
        """
        The list of references listed below represent real
        references of datasets that are imported using the
        fixture file. Each reference is passed to the
        corresponding fetcher function.
        """
        self.rfcs_ref = "RFC.4037"
        self.misc_ref = "FIPS.180.1993"  # fix
        self.internet_drafts_ref = "I-D.ietf-hip-rfc5201-bis"
        self.w3c_ref = "W3C.REC-owl2-syntax-20121211"  # fix
        self.threegpp_ref = "SDO-3GPP.TS 25.321:Rel-8/8.3.0"  # fix
        self.ieee_ref = "R.IEEE.P2740/D-6.5.2020-08"
        self.iana_ref = "IANA.xml-security-uris/security-uris"
        self.rfcsubseries_ref = "STD.29.xml"
        self.nist_ref = "NBS.CRPL-F-A.90"  # fix
        self.doi_ref = "10.1093/benz/9780199773787.article.b00004912"

        self.dirname = XML2RFC_PATH_PREFIX

    def _assert_refs_equal(self, bibitem, ref):
        for id in bibitem.docid:
            if id.scope == 'anchor':
                self.assertEqual(id.id, ref)

    def _assert_is_instance_of_bibliographicitem(self, obj):
        self.assertIsInstance(obj, BibliographicItem)

    def test_rfcs(self):
        adapter = RfcAdapter(self.dirname, "bibxml1", self.rfcs_ref)
        bibitem = adapter.resolve()
        self._assert_is_instance_of_bibliographicitem(bibitem)
        self._assert_refs_equal(bibitem, self.rfcs_ref.replace(".", ""))

    def test_rfcs_not_found(self):
        adapter = RfcAdapter(self.dirname, "bibxml1", "NONEXISTENT.403799999991")
        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    def test_misc(self):
        # TODO fix
        # adapter = MiscAdapter(self.dirname, "bibxml2", self.misc_ref)
        # bibitem = adapter.resolve()
        # self._assert_is_instance_of_bibliographicitem(bibitem)
        # self._assert_refs_equal(bibitem, self.misc_ref)
        pass

    def test_misc_not_found(self):
        adapter = MiscAdapter(self.dirname, "bibxml2", "NONEXISTENT.8023.19888")
        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    def test_internet_drafts(self):
        adapter = InternetDraftsAdapter(self.dirname, "bibxml3", self.internet_drafts_ref)
        bibitem = adapter.resolve()
        self._assert_is_instance_of_bibliographicitem(bibitem)
        self._assert_refs_equal(bibitem, self.internet_drafts_ref)

    def test_internet_drafts_not_found(self):
        adapter = InternetDraftsAdapter(self.dirname, "bibxml3", self.internet_drafts_ref.replace("b", ""))

        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    def test_internet_drafts_invalid_ref(self):
        adapter = InternetDraftsAdapter(self.dirname, "bibxml3", self.internet_drafts_ref.replace("b", ""))
        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    def test_w3c(self):
        """
        This test fails with some old data representation. Relatons data should conform
        to the official schema https://github.com/relaton/relaton-models/blob/main/grammars/biblio.rnc
        pydantic.error_wrappers.ValidationError: 1 validation error for BibliographicItem
        relation -> 0 -> bibitem -> formattedref
        instance of GenericStringValue, tuple or dict expected (type=type_error.dataclass; class_name=GenericStringValue)
        """
        # TODO fix
        # "W3C.REC-owl2-syntax-20121211"
        # adapter = W3cAdapter(self.dirname, "bibxml4", self.w3c_ref)
        # bibitem = adapter.resolve()
        # self._assert_is_instance_of_bibliographicitem(bibitem)
        # self._assert_refs_equal(bibitem, self.w3c_ref)
        pass

    def test_w3c_not_found(self):
        adapter = W3cAdapter(self.dirname, "bibxml4", self.w3c_ref)
        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    def test_threegpp(self):
        # TODO fix
        # adapter = ThreeGPPPAdapter(self.dirname, "bibxml5", self.threegpp_ref)
        # bibitem = adapter.resolve()
        # self._assert_refs_equal(bibitem, self.threegpp_ref)
        pass

    def test_threegpp_not_found(self):
        adapter = ThreeGPPPAdapter(self.dirname, "bibxml5", self.threegpp_ref+"AA")
        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    def test_ieee(self):
        adapter = IeeeAdapter(self.dirname, "bibxml6", self.ieee_ref)
        bibitem = adapter.resolve()
        self._assert_is_instance_of_bibliographicitem(bibitem)
        self._assert_refs_equal(bibitem, self.ieee_ref)

    def test_ieee_not_found(self):
        adapter = IeeeAdapter(self.dirname, "bibxml6", self.ieee_ref+"AA")
        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    # def test_doi(self):
    #     self._assert_is_instance_of_bibliographicitem(fetchers.doi(ref=self.doi_ref))
    #
    # def test_doi_not_found(self):
    #     with self.assertRaises(RefNotFoundError):
    #         fetchers.doi(ref="NONEXISTENT_REF")

    def test_iana(self):
        adapter = IanaAdapter(self.dirname, "bibxml8", self.iana_ref)
        bibitem = adapter.resolve()
        self._assert_is_instance_of_bibliographicitem(bibitem)

    def test_iana_not_found(self):
        adapter = IanaAdapter(self.dirname, "bibxml8", self.iana_ref+"AA")
        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    def test_rfcsubseries(self):
        adapter = RfcSubseriesAdapter(self.dirname, "bibxml9", self.rfcs_ref)
        bibitem = adapter.resolve()
        self._assert_is_instance_of_bibliographicitem(bibitem)

    def test_rfcsubseries_not_found(self):
        adapter = RfcSubseriesAdapter(self.dirname, "bibxml9", self.rfcs_ref+"1")
        with self.assertRaises(RefNotFoundError):
            adapter.resolve()

    def test_nist(self):
        # TODO fix
        # adapter = RfcSubseriesAdapter(self.dirname, "bibxml-nist", self.nist_ref)
        # bibitem = adapter.resolve()
        # self._assert_is_instance_of_bibliographicitem(bibitem)
        # self._assert_refs_equal(bibitem, self.nist_ref)
        pass

    def test_nist_not_found(self):
        # TODO fix
        # adapter = RfcSubseriesAdapter(self.dirname, "bibxml-nist", self.nist_ref)
        # with self.assertRaises(RefNotFoundError):
        #     adapter.resolve()
        pass

