import datetime
from typing import Dict, Any
from urllib.parse import quote_plus
import json

from django.test import TestCase
from django.urls import reverse

from .models import RefData


class RefDataModelTests(TestCase):
    """
    If we make "service" instances read only, this test will fail,
    and at least setUp() should be rewritten.
    """

    def setUp(self):
        self.ref_id = "ref_01"
        self.dataset_name = 'nist'
        self.ref_body: Dict[str, Any] = {
            "id": "ref_01",
            "docid": [{"id": "ref_01", "type": "test_dataset_01"}],
            "date": {"type": "published", "value": "2000-01-01"},
            "doctype": "standart",
            "language": ["en"],
            "script": "Latn",
            "title": [
                {
                    "type": "title-main",
                    "content": "Lorem Ipsum Dolor Sit Amet",
                    "format": "text/plain",
                    "language": "en",
                }
            ],
        }

        self.ref1 = RefData.objects.create(
            ref=self.ref_id,
            dataset=self.dataset_name,
            body=self.ref_body,
            representations={},
            latest_date=datetime.datetime.now().date()
        )
        import datatracker.auth
        datatracker.auth.token_is_valid = lambda key: True

        self.api_headers = {
            'HTTP_X_DATATRACKER_TOKEN': 'test',
        }

    def test_get_ref(self):
        docid = self.ref_body['docid'][0]['id']
        url = f'%s?docid={docid}' % reverse("api_get_by_docid")
        response = self.client.get(url, **self.api_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['data']['id'], self.ref_body['id'])

    def test_not_found_ref(self):
        url = '%s?docid=NONEXISTENTKEY404' % reverse("api_get_by_docid")
        response = self.client.get(url, **self.api_headers)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(len(response.json()["error"]) > 0)

    def test_success_search_ref(self):
        struct_query = json.dumps(
            {
                "doctype": "standart", "id": "ref_01",
            }
        )
        url = '%s?query_format=json_struct' % reverse(
            "api_search",
            args=[quote_plus(struct_query)],
        )
        response = self.client.get(
            url,
            content_type="application/json",
            **self.api_headers,
        )

        self.assertEqual(response.status_code, 200)

        found_obj = response.json().get("data")[0]
        # strip None values
        found_obj_doc_id = [{k: v for k, v in found_obj['docid'][0].items() if v is not None}]

        self.assertEqual(found_obj['id'], self.ref_body['id'])
        self.assertEqual(found_obj_doc_id, self.ref_body['docid'])

    def test_fail_search_ref(self):
        struct_query = json.dumps(
            {
                "doctype": "standart", "id": "NONEXISTENTID404",
            }
        )
        url = '%s?query_format=json_struct' % reverse(
            "api_search",
            args=[quote_plus(struct_query)],
        )
        response = self.client.get(
            url,
            content_type="application/json",
            **self.api_headers,
        )

        self.assertEqual(response.status_code, 200)

        results_count = len(response.json().get("data"))

        self.assertEqual(results_count, 0)

    def test_get_doi_ref(self):
        pass
        # TODO: Shall we have here a static external reference/DOI to use for testing?
        # url = f'{reverse("api_get_doi_ref", kwargs={"ref": self.ref_id})}'
        # response = self.client.get(url, **self.api_headers)
        # self.assertEqual(response.status_code, 200)
        # self.assertEqual(json.loads(response.content)['data']['id'], self.ref_body['id'])

    def test_not_found_by_doi_ref(self):
        url = f'{reverse("api_get_doi_ref", kwargs={"ref": "NONEXISTENTREF404"})}'
        response = self.client.get(url, **self.api_headers)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(len(response.json()["error"]) > 0)
