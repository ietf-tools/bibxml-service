"""Adds ``refdata_docid_keys()`` and a GIN index over it.

``like_regex`` cannot use ``body_gin``, so a docid jsonpath such as
``@.type == "W3C" && @.id like_regex "..."`` is rechecked against every row
of the doctype. The index lets callers put
``refdata_docid_keys(body) && ARRAY[keys]`` in front of that jsonpath as a
candidate filter.

For every ``docid[*].id`` the function returns the id lower-cased with each
non-alphanumeric character replaced by ``-``, plus that key with a trailing
``-NN`` stripped. The first form is the equivalence class
``common.util.get_fuzzy_match_regex`` matches, so a normalised request key
is a superset of the regex; the second lets an unversioned Internet-Draft
name key every version. ``main.query.normalize_docid_key`` must produce the
same first form, and ``main.tests.test_docid_keys`` pins the two together.

Case-folding happens after the string is reduced to ASCII, so the output
does not depend on the database's LC_CTYPE (production is ``C``; CI is not).
``IMMUTABLE`` is required for an expression index.

Built ``CONCURRENTLY`` (hence ``atomic = False``) so the build waits for
in-flight indexer transactions instead of blocking them behind a SHARE lock.
An interrupted build leaves an INVALID ``body_docid_keys_gin`` that must be
dropped by hand before the migration is re-run.
"""

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


CREATE_FUNCTION = """
CREATE OR REPLACE FUNCTION refdata_docid_keys(body jsonb) RETURNS text[]
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS $$
  SELECT coalesce(array_agg(DISTINCT key), '{}'::text[])
  FROM (
    SELECT lower(regexp_replace(d->>'id', '[^a-zA-Z0-9]', '-', 'g')) AS k
      FROM jsonb_array_elements(
        CASE jsonb_typeof(body->'docid')
          WHEN 'array' THEN body->'docid'
          WHEN 'object' THEN jsonb_build_array(body->'docid')
          ELSE '[]'::jsonb
        END) AS d
     WHERE jsonb_typeof(d->'id') = 'string'
  ) AS norm,
  LATERAL unnest(ARRAY[norm.k, regexp_replace(norm.k, '-[0-9]{2}$', '')])
    AS key
$$;
"""

DROP_FUNCTION = "DROP FUNCTION IF EXISTS refdata_docid_keys(jsonb);"


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('main', '0010_drop_unused_body_gin_indexes'),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_FUNCTION, reverse_sql=DROP_FUNCTION),
        AddIndexConcurrently(
            model_name='refdata',
            index=GinIndex(
                models.Func(
                    models.F('body'),
                    function='refdata_docid_keys',
                    output_field=ArrayField(models.TextField()),
                ),
                name='body_docid_keys_gin',
            ),
        ),
    ]
