import datetime
import tempfile
from pathlib import Path
from typing import Any, Dict

import yaml
from django.test import TestCase

from main.models import RefData
from main.sources import index_dataset


DATASET = 'test-ds'


def _body(ref: str) -> Dict[str, Any]:
    """Minimal Relaton-shaped body. ``date`` is omitted deliberately so that
    :func:`main.sources.index_dataset` falls back to today's date and the test
    does not depend on Relaton date parsing."""
    return {
        'id': ref,
        'docid': [{'id': ref, 'type': 'test', 'primary': True}],
    }


class IndexDatasetDeletionTests(TestCase):
    """Guards which refs :func:`main.sources.index_dataset` deletes.

    The partial-reindex branch used to ``exclude()`` the missing refs rather
    than ``filter()`` them, so a successful partial reindex deleted the whole
    dataset. These tests pin the intended behaviour in both directions.
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.source_path = Path(self.tmpdir.name)

        # Source contains A and B.
        for ref in ('A', 'B'):
            (self.source_path / f'{ref}.yaml').write_text(
                yaml.safe_dump(_body(ref)), encoding='utf-8')

        # The database additionally contains C, which is no longer in source.
        for ref in ('A', 'B', 'C'):
            RefData.objects.create(
                ref=ref,
                dataset=DATASET,
                body=_body(ref),
                representations={},
                latest_date=datetime.date(2020, 1, 1),
            )

    def _refs(self):
        return set(
            RefData.objects.
            filter(dataset=DATASET).
            values_list('ref', flat=True))

    def test_partial_reindex_keeps_refs_outside_the_request(self):
        """Reindexing a subset must not touch refs that were not requested."""
        index_dataset(DATASET, str(self.source_path), refs=['A'])

        self.assertEqual(self._refs(), {'A', 'B', 'C'})

    def test_partial_reindex_deletes_requested_refs_absent_from_source(self):
        """A requested ref that is missing from source is the one to delete."""
        index_dataset(DATASET, str(self.source_path), refs=['A', 'C'])

        self.assertEqual(self._refs(), {'A', 'B'})

    def test_partial_reindex_updates_the_requested_ref(self):
        (self.source_path / 'A.yaml').write_text(
            yaml.safe_dump({**_body('A'), 'title': 'updated'}),
            encoding='utf-8')

        index_dataset(DATASET, str(self.source_path), refs=['A'])

        self.assertEqual(
            RefData.objects.get(ref='A', dataset=DATASET).body['title'],
            'updated')

    def test_full_reindex_deletes_refs_absent_from_source(self):
        """Unchanged behaviour: a full pass prunes anything not in source."""
        index_dataset(DATASET, str(self.source_path))

        self.assertEqual(self._refs(), {'A', 'B'})

    def test_deletion_is_scoped_to_the_dataset(self):
        RefData.objects.create(
            ref='A',
            dataset='other-ds',
            body=_body('A'),
            representations={},
            latest_date=datetime.date(2020, 1, 1),
        )

        index_dataset(DATASET, str(self.source_path), refs=['A'])

        self.assertTrue(
            RefData.objects.filter(dataset='other-ds', ref='A').exists())
