from typing import Dict
from unittest import TestCase

from bib_models import DocID
from main.query_utils import get_docid_struct_for_search, get_primary_docid


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

    def test_get_primary_docid(self):
        primary_id_value = "primary_id_value"
        raw_ids = [
            DocID(id=primary_id_value, type="type", primary=True),
            DocID(id="id2", type="type2", primary=False),
            DocID(id="id3", type="type3", scope="scope", primary=False)
        ]
        primary_id = get_primary_docid(raw_ids)
        self.assertIsInstance(primary_id, DocID)
        self.assertEqual(primary_id.id, primary_id_value)

    def test_fail_get_primary_docid_if_no_primary_id(self):
        """
        get_primary_docid should return None if no entry has primary == True
        """
        primary_id_value = "primary_id_value"
        raw_ids = [
            DocID(id=primary_id_value, type="type", primary=False),
            DocID(id="id2", type="type2", primary=False),
            DocID(id="id3", type="type3", scope="scope", primary=False)
        ]
        self.assertIsNone(get_primary_docid(raw_ids))
