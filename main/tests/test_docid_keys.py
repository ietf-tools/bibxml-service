"""Tests for the normalised-docid lookup path (migration 0011).

The key filter added by ``docid_keys=`` is a *hard* filter, so a mismatch
between the SQL and Python normalisers would make a reference silently
unresolvable rather than slow. The first tests below pin the two together;
the rest exercise the query shapes the xml2rfc adapters emit.
"""

import json
from typing import List

from django.db import connection
from django.test import TestCase

from common.util import get_fuzzy_match_regex
from main.query import (
    normalize_docid_key,
    search_refs_docids,
    search_refs_relaton_field,
)


def sql_docid_keys(*ids: str) -> List[str]:
    body = json.dumps({'docid': [{'id': i, 'type': 'X'} for i in ids]})
    with connection.cursor() as cursor:
        cursor.execute("SELECT refdata_docid_keys(%s::jsonb)", [body])
        return cursor.fetchone()[0]


def fuzzy_docid_query(doctype: str, docid: str) -> str:
    """Mirrors ``xml2rfc_compat.adapters.get_docid_query(exact=False)``."""
    return (
        '@.type == "%s" && @.primary == true && @.id like_regex "(?i)^%s$"'
        % (doctype, get_fuzzy_match_regex(docid))
    )


class DocidKeysTestCase(TestCase):
    fixtures = ['test_refdata.json']

    def test_index_created_by_migration(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'api_ref_data' "
                "AND indexname = 'body_docid_keys_gin'")
            row = cursor.fetchone()
        self.assertIsNotNone(row, "body_docid_keys_gin is missing")
        self.assertIn('USING gin (refdata_docid_keys(body))', row[0])

    def test_python_normaliser_agrees_with_sql(self):
        samples = [
            'RFC 4037',
            'W3C REC-powder-grouping-20090901',
            'IEEE P2740/D-6.5.2020-08',
            'IEEE PC37.122™/D-19-2010-06',   # trademark sign
            '3GPP TS 25.321:Rel-8/8.3.0',
            'IANA xml-security-uris/security-uris',
            'draft-ietf-hip-rfc5201-bis-13',
            'MiXeD CaSe   with  spaces',
            'Ünicode Élan-1',            # non-ASCII letters
            '',
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertIn(
                    normalize_docid_key(sample), sql_docid_keys(sample))

    def test_sql_keys_include_version_stripped_form(self):
        keys = sql_docid_keys('draft-ietf-hip-rfc5201-bis-13')
        self.assertCountEqual(keys, [
            'draft-ietf-hip-rfc5201-bis-13',
            'draft-ietf-hip-rfc5201-bis',
        ])
        # Only an exact trailing -NN is treated as a version.
        self.assertCountEqual(sql_docid_keys('RFC 4037'), ['rfc-4037'])

    def test_sql_keys_tolerate_odd_docid_shapes(self):
        with connection.cursor() as cursor:
            for body in (
                '{}',
                '{"docid": null}',
                '{"docid": []}',
                '{"docid": {"id": "RFC 1", "type": "IETF"}}',
                '{"docid": [{"type": "IETF"}, {"id": 5}]}',
            ):
                with self.subTest(body=body):
                    cursor.execute(
                        "SELECT refdata_docid_keys(%s::jsonb)", [body])
                    self.assertIsInstance(cursor.fetchone()[0], list)

    def test_normalize_docid_key(self):
        self.assertEqual(normalize_docid_key('W3C soap11'), 'w3c-soap11')
        self.assertEqual(normalize_docid_key('W3C.soap11'), 'w3c-soap11')
        self.assertEqual(
            normalize_docid_key('ANSI X3.4-1986'), 'ansi-x3-4-1986')
        # One separator per non-alphanumeric character, like the regex.
        self.assertEqual(normalize_docid_key('a  b'), 'a--b')

    def test_keyed_lookup_ignores_case_and_separators(self):
        # The anchor a client would request for the W3C fixture row,
        # deliberately mangled the way legacy xml2rfc paths are.
        requested = 'w3c rec_POWDER.grouping-20090901'
        refs = list(search_refs_relaton_field(
            {'docid[*]': fuzzy_docid_query('W3C', requested)},
            exact=True,
            limit=10,
            docid_keys=[normalize_docid_key(requested)],
        ))
        self.assertEqual(
            [r.ref for r in refs], ['rec-powder-grouping-20090901'])

    def test_key_filter_is_applied(self):
        # Same jsonpath as above, but a key that matches nothing: the key
        # filter must exclude the row, which is why the keys passed in
        # must always be a superset of what the jsonpath can match.
        requested = 'W3C REC-powder-grouping-20090901'
        refs = search_refs_relaton_field(
            {'docid[*]': fuzzy_docid_query('W3C', requested)},
            exact=True,
            limit=10,
            docid_keys=['not-a-real-key'],
        )
        self.assertEqual(len(refs), 0)

    def test_no_keys_behaves_as_before(self):
        requested = 'W3C REC-powder-grouping-20090901'
        refs = search_refs_relaton_field(
            {'docid[*]': fuzzy_docid_query('W3C', requested)},
            exact=True,
            limit=10,
        )
        self.assertEqual(len(refs), 1)

    def test_unversioned_internet_draft_lookup(self):
        # Mirrors InternetDraftsAdapter.fetch_refs() for an unversioned path.
        unversioned = 'ietf-hip-rfc5201-bis'
        query = (
            '(@.type == "Internet-Draft") && '
            r'(@.id like_regex '
            r'"draft\-ietf\-hip\-rfc5201\-bis\-[[:digit:]]{2}")'
        )
        refs = list(search_refs_relaton_field(
            {'docid[*]': query},
            exact=True,
            limit=50,
            docid_keys=[normalize_docid_key(f'draft-{unversioned}')],
        ))
        self.assertEqual(
            [r.ref for r in refs], ['draft-ietf-hip-rfc5201-bis-13'])

    def test_search_refs_docids_case_insensitive_fallback(self):
        # The exact @> lookup misses on case; the like_regex fallback,
        # now keyed, must still find it.
        refs = list(search_refs_docids('rfc 4037'))
        self.assertEqual([r.ref for r in refs], ['RFC4037'])
