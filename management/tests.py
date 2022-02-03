from django.test import TestCase, Client
from django.db.utils import IntegrityError
from django.conf import settings
from django.urls import reverse

from main.models import RefData


class RefDataModelTests(TestCase):
    def setUp(self):
        self.dataset1_name = "test_dataset_01"
        self.dataset2_name = "test_dataset_02"
        self.ref_body = {}

    def test_fail_duplicate_ref(self):
        self.ref1 = RefData.objects.create(
            ref="ref_01", dataset=self.dataset1_name, body=self.ref_body, representations={},
        )

        self.assertRaises(
            IntegrityError,
            RefData.objects.create,
            ref="ref_01",
            dataset=self.dataset1_name,
            body=self.ref_body,
            representations={},
        )

    def test_same_ref_diff_datasets(self):
        self.ref1 = RefData.objects.create(
            ref="ref_01", dataset=self.dataset1_name, body=self.ref_body, representations={},
        )
        self.ref2 = RefData.objects.create(
            ref="ref_01", dataset=self.dataset2_name, body=self.ref_body, representations={},
        )


class IndexerTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.real_dataset = list(settings.RELATON_DATASETS)[0]

    def test_run_indexer(self):
        """
        TODO:
            We need to create test dataset at some remote repo
            and make more complicated integration test.
            Or make it with self.real_dataset?
            But it can be unnecessary a waste of resources.
        """
        pass

    # NOTE: To test index process abortion, we need to test new stop_task() API;
    # but let’s be mindful about not testing Celery itself and perhaps mock things instead.
    # def test_stop_indexer(self):
    #     url = reverse("api_stop_indexer", args=[self.real_dataset])
    #     response = self.client.get(url)

    #     # Should get error when we trying to stop not running indexer:
    #     self.assertEqual(response.status_code, 500)
    #     self.assertTrue(len(response.json()["error"]) > 0)

    def test_reset_indexer(self):
        url = reverse("api_reset_index", args=[self.real_dataset])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RefData.objects.count() == 0)

    def test_indexer_status(self):
        url = reverse("api_indexer_status", args=[self.real_dataset])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()["tasks"]) > 0)
