"""Declares the pre-existing ``body_json_ts_gin`` index.

This index was created out-of-band in production and never had a migration,
so ``manage.py test`` and any fresh deploy got a schema that differed from
production on the index backing the whole-body websearch.

The DDL is wrapped in ``SeparateDatabaseAndState`` because the two
environments disagree:

* in production the index already exists, so a plain ``AddIndex`` would emit
  ``CREATE INDEX`` for an existing name and fail the deploy;
* in a fresh or test database it does not exist and must be created.

``CREATE INDEX IF NOT EXISTS`` satisfies both, while the state operation
keeps Django's model state in step so ``makemigrations`` stays quiet.
``CONCURRENTLY`` is not used: this path only runs against databases that
lack the index, which are empty at migrate time.
"""

import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_refdata_latest_date'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddIndex(
                    model_name='refdata',
                    index=django.contrib.postgres.indexes.GinIndex(
                        models.Func(
                            models.Value('english'),
                            models.F('body'),
                            function='to_tsvector',
                            output_field=(
                                django.contrib.postgres.search
                                .SearchVectorField()
                            ),
                        ),
                        name='body_json_ts_gin',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'CREATE INDEX IF NOT EXISTS "body_json_ts_gin" '
                        'ON "api_ref_data" '
                        'USING gin ((to_tsvector(\'english\', "body")));'
                    ),
                    reverse_sql=(
                        'DROP INDEX IF EXISTS "body_json_ts_gin";'
                    ),
                ),
            ],
        ),
    ]
