import json
from django.test import TestCase, Client
from django.conf import settings
from django.urls import reverse

from .models import RefData


class RefDataModelTests(TestCase):
    """
    If we make "service" instances read only, this test will fail,
    and at least setUp() should be rewritten.
    """

    def setUp(self):
        self.ref_id = "ref_01"
        self.dataset_name = list(settings.INDEXABLE_DATASETS)[0]
        self.ref_type = "standart"
        self.ref_body = {
            "id": "ref_01",
            "docid": {"id": "ref_01", "type": "test_dataset_01"},
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
            ref_id=self.ref_id,
            dataset=self.dataset_name,
            ref_type=self.ref_type,
            body=self.ref_body,
        )

    def test_get_ref(self):
        url = reverse(
            "api_get_ref", kwargs={"lib": self.dataset_name, "ref": self.ref_id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"data": self.ref_body})

    def test_not_found_ref(self):
        url = reverse(
            "api_get_ref",
            kwargs={"lib": self.dataset_name, "ref": "NOTEXISTSKEY404"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(len(response.json()["error"]) > 0)

    def test_success_search_ref(self):
        url = reverse("api_search")
        response = self.client.post(
            url,
            json.dumps(
                {
                    "dataset": self.dataset_name,
                    "fields": {"doctype": "standart", "id": "ref_01"},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        found_obj = json.dumps(response.json().get("data")[0].get("body"))

        self.assertJSONEqual(found_obj, self.ref_body)

    def test_fail_search_ref(self):
        url = reverse("api_search")
        response = self.client.post(
            url,
            json.dumps(
                {
                    "dataset": self.dataset_name,
                    "fields": {"doctype": "standart", "id": "NOTEXISTSKEY404"},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        results_count = int(response.json().get("results").get("records"))

        self.assertEqual(results_count, 0)
