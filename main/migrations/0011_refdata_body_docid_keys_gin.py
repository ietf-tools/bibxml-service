"""Adds ``refdata_docid_keys()`` and a GIN index over it, so xml2rfc docid
lookups can be keyed instead of regex-scanning every row of a doctype.

Nine of the ten xml2rfc adapters look a document up with a jsonpath such as::

    $.docid[*] ? (@.type == "W3C" && @.primary == true
                  && @.id like_regex "(?i)^W3C[^a-zA-Z0-9]soap11$")

PostgreSQL can only feed the ``==`` clauses to ``body_gin``; ``like_regex``
contributes nothing, so the index returns every row of that doctype (167,500
for Internet-Drafts) and the regex is rechecked per row with a JSONB detoast.
Measured in production this one query shape was 94.8% of all database
execution time, at a mean of 2.4 s per call.

``refdata_docid_keys(body)`` returns, for every ``docid[*].id`` in a body:

* the id lower-cased with every non-alphanumeric character replaced by ``-``
  -- exactly the equivalence class ``common.util.get_fuzzy_match_regex``
  matches, so ``key = normalize(request)`` is a superset of the regex; and
* that key with a trailing ``-NN`` stripped, so an unversioned Internet-Draft
  lookup (``draft-foo-[[:digit:]]{2}``) can be keyed on ``draft-foo``.

Queries add ``refdata_docid_keys(body) && ARRAY[keys]`` *alongside* the
original jsonpath, which is retained as the exact recheck; the key filter
only has to be a superset, never an equivalent. The Python side of the
normalisation is ``main.query.normalize_docid_key`` and a test pins the two
to each other.

The function is ``IMMUTABLE`` (required for an expression index) and does
its case-folding after reducing the string to ASCII, so its output does not
depend on the database's LC_CTYPE (production is ``C``; CI is not).

Built ``CONCURRENTLY`` -- hence ``atomic = False`` -- for the same reason
0010 dropped concurrently: a plain ``CREATE INDEX`` takes SHARE on
``api_ref_data`` and would block the indexer for the duration. On the
restored production dump the build took 7 s at production's
``maintenance_work_mem = 64MB`` and produced a 43 MB index. If it is
interrupted it leaves an INVALID ``body_docid_keys_gin`` behind that must be
``DROP INDEX``-ed by hand before the migration can be re-run.
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
