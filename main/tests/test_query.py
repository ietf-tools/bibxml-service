import re
from unittest import TestCase

from django.core.management import call_command
from django.db.models import QuerySet

from main.query import search_refs_relaton_field, list_refs, list_doctypes


class QueryTestCase(TestCase):

    def setUp(self) -> None:
        call_command('loaddata', 'xml2rfc_compat/fixtures/test_refdata.json')

    def test_list_refs(self):
        dataset_id = 'rfcs'
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
        limit = 10
        refs = search_refs_relaton_field({
            'docid[*]': '@.id == "%s"'
            % re.escape("IEEE.802-3.1988"),
        }, limit=limit, exact=True)
        self.assertIsInstance(refs, QuerySet)
        self.assertGreater(refs.count(), 0)
        self.assertLess(refs.count(), limit)

    def test_search_refs_relaton_field_without_field_queries(self):
        refs = search_refs_relaton_field()
        self.assertIsInstance(refs, QuerySet)
        self.assertEqual(refs.count(), 0)
