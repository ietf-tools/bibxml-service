import json
import re
from unittest import TestCase

from django.core.management import call_command
from django.db.models import QuerySet, Q

from main.exceptions import RefNotFoundError
from main.models import RefData
from main.query import (
    search_refs_relaton_field,
    list_refs,
    list_doctypes,
    search_refs_docids,
    build_citation_for_docid,
    build_search_results,
    get_indexed_item,
    get_indexed_ref_by_query,
)
from main.types import CompositeSourcedBibliographicItem, IndexedBibliographicItem


class QueryTestCase(TestCase):
    def setUp(self) -> None:
        call_command("loaddata", "xml2rfc_compat/fixtures/test_refdata.json")

        with open("xml2rfc_compat/fixtures/test_refdata.json", "r") as f:
            self.json_fixtures = json.load(f)

    def _get_list_of_docids_for_dataset_from_fixture(self, dataset="rfcs"):
        return [
            item["fields"]["body"]["docid"]
            for item in self.json_fixtures
            if item["fields"]["dataset"] == dataset
        ][0]

    def test_list_refs(self):
        dataset_id = "rfcs"
        rfcs_refs_queryset = list_refs(dataset_id)
        self.assertGreater(rfcs_refs_queryset.count(), 0)

        non_rfcs_queryset = rfcs_refs_queryset.exclude(dataset__iexact=dataset_id)
        self.assertEqual(non_rfcs_queryset.count(), 0)

    def test_list_doctypes(self):
        doctypes = list_doctypes()
        self.assertIsInstance(doctypes, list)
        self.assertGreater(len(doctypes), 0)
        self.assertIsInstance(doctypes[0], tuple)

    def test_search_refs_relaton_field(self):
        docids = self._get_list_of_docids_for_dataset_from_fixture("misc")
        docid = next(docid["id"] for docid in docids if docid.get("scope") == "anchor")

        limit = 10
        refs = search_refs_relaton_field(
            {
                "docid[*]": '@.id == "%s"' % re.escape(docid),
            },
            limit=limit,
            exact=True,
        )
        self.assertIsInstance(refs, QuerySet[RefData])
        self.assertGreater(refs.count(), 0)
        self.assertLess(refs.count(), limit)

    def test_search_refs_relaton_field_without_field_queries(self):
        refs = search_refs_relaton_field()
        self.assertIsInstance(refs, QuerySet[RefData])
        self.assertEqual(refs.count(), 0)

    def test_search_refs_docids(self):
        docids = self._get_list_of_docids_for_dataset_from_fixture()
        docids = [item["id"] for item in docids]
        refs = search_refs_docids(*docids)
        self.assertIsInstance(refs, QuerySet[RefData])
        self.assertGreater(refs.count(), 0)

    def test_build_citation_for_docid(self):
        docids = self._get_list_of_docids_for_dataset_from_fixture()
        for docid in docids:
            id, doctype = docid["id"], docid["type"]
            citation = build_citation_for_docid(id, doctype)
            self.assertIsInstance(citation, CompositeSourcedBibliographicItem)

    def test_build_citation_for_nonexistent_docid(self):
        id, doctype = "NONEXISTENTID", "NONEXISTENTTYPE"
        with self.assertRaises(RefNotFoundError):
            build_citation_for_docid(id, doctype)

    def test_build_search_results(self):
        docids = self._get_list_of_docids_for_dataset_from_fixture("misc")
        docid = next(docid["id"] for docid in docids if docid.get("scope") == "anchor")

        limit = 10
        refs = search_refs_relaton_field(
            {
                "docid[*]": '@.id == "%s"' % re.escape(docid),
            },
            limit=limit,
            exact=True,
        )

        found_items = build_search_results(refs)
        self.assertIsInstance(found_items, list)
        self.assertGreater(len(found_items), 0)

    def test_build_search_empty_results(self):
        limit = 10
        refs = search_refs_relaton_field(
            {
                "docid[*]": '@.id == "%s"' % re.escape("NONEXISTENTID"),
            },
            limit=limit,
            exact=True,
        )

        found_items = build_search_results(refs)
        self.assertIsInstance(found_items, list)
        self.assertEqual(len(found_items), 0)

    def test_get_indexed_item(self):
        dataset_object = [
            item["fields"]
            for item in self.json_fixtures
            if item["fields"]["dataset"] == "rfcs"
        ][0]
        dataset, ref = dataset_object["dataset"], dataset_object["ref"]
        indexed_item = get_indexed_item(dataset, ref)
        self.assertIsInstance(indexed_item, IndexedBibliographicItem)

    def test_get_indexed_ref_by_query(self):
        dataset_object = [
            item["fields"]
            for item in self.json_fixtures
            if item["fields"]["dataset"] == "rfcs"
        ][0]
        dataset, ref = dataset_object["dataset"], dataset_object["ref"]
        data = get_indexed_ref_by_query(dataset, Q(ref__iexact=ref))
        self.assertIsInstance(data, RefData)

    def test_get_indexed_ref_by_query_unexistent_ref(self):
        dataset, ref = "NONEXISTING_DATASET", "NONEXISTING_REF"
        with self.assertRaises(RefNotFoundError):
            get_indexed_ref_by_query(dataset, Q(ref__iexact=ref))
