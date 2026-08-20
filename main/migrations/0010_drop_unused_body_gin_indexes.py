"""Drops three GIN indexes on ``api_ref_data.body`` that no query can reach.

* ``body_astext_gin`` and ``body_ts_gin`` are byte-identical DDL --
  ``SearchVector('body')`` on a JSONField casts to text exactly like
  ``SearchVector(Cast('body', TextField()))`` -- so one was always redundant
  with the other.
* ``body_docid_gin`` indexes ``to_tsvector('english', (body->'docid')::text)``.

No query in the codebase emits any of those expressions. ``main.query`` only
ever produces ``body @?``/``body @>`` (served by ``body_gin``),
``to_tsvector('english', body)`` (the jsonb overload, served by
``body_json_ts_gin``) and ``to_tsvector('english', jsonb_build_array(...))``,
which matches no index. The commented-out
``annotate(search=SearchVector(Cast('body', TextField())))`` in main/query.py
is the abandoned approach these were built for.

Production confirms it: over roughly eleven days of ``pg_stat_user_indexes``
counters, covering many full reindex cycles, all three recorded zero scans.
Together they were 617MB of the table's 1215MB of indexes.

Dropped ``CONCURRENTLY`` -- hence ``atomic = False`` -- because a plain
``DROP INDEX`` takes ACCESS EXCLUSIVE on ``api_ref_data``: the lock request
queues behind any in-flight query and every subsequent query queues behind
the lock request, which would stall the table.

Note that ``api_ref_data_ref_dataset_3182f6b6_uniq`` also shows zero scans
but is NOT dropped here: it enforces the ``unique_together`` constraint.
"""

from django.contrib.postgres.operations import RemoveIndexConcurrently
from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('main', '0009_refdata_body_json_ts_gin'),
    ]

    operations = [
        RemoveIndexConcurrently(
            model_name='refdata',
            name='body_astext_gin',
        ),
        RemoveIndexConcurrently(
            model_name='refdata',
            name='body_ts_gin',
        ),
        RemoveIndexConcurrently(
            model_name='refdata',
            name='body_docid_gin',
        ),
    ]
