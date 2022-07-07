from typing import Dict
from unittest import TestCase

from bib_models import DocID
from main.query_utils import get_docid_struct_for_search


class QueryTestCase(TestCase):
    """
    Test cases for query_utils.py
    """

    def test_get_docid_struct_for_search(self):
        id_value = "ID"
        type_value = "TYPE"
        docid = DocID(id=id_value, type=type_value, primary=True)
        struct = get_docid_struct_for_search(docid)
        self.assertIsInstance(struct, Dict)
        self.assertEqual(struct["id"], id_value)
        self.assertEqual(struct["type"], type_value)
        self.assertTrue(struct["primary"])

        # if DocID.primary = False, struct should not include "primary" key
        docid = DocID(id=id_value, type=type_value, primary=False)
        struct = get_docid_struct_for_search(docid)
        self.assertIsInstance(struct, Dict)
        self.assertEqual(struct["id"], id_value)
        self.assertEqual(struct["type"], type_value)
        self.assertIsNone(struct.get("primary", None))
