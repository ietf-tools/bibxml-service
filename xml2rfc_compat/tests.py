from copy import copy
from typing import Dict, Any

from django.test import TestCase
from lxml import etree

from bib_models import BibliographicItem, Contributor
from xml2rfc_compat.serializer import to_xml, create_reference, create_author


class XML2RFCTestCase(TestCase):
    def setUp(self):
        self.contributor_organization_data = {
            "organization": {
                "name": "Internet Engineering Task Force",
            },
            "role": "publisher",
        }
        self.contributor_person_data = {
            "person": {
                "name": {
                    "initial": [{"content": "Mr", "language": "en"}],
                    "surname": {"content": "Cerf", "language": "en"},
                    "completename": {"content": "Mr Cerf", "language": "en"},
                },
            },
            "role": "author",
        }
        self.bibitem_data: Dict[str, Any] = {
            "id": "ref_01",
            "title": [
                {
                    "content": "title",
                    "language": "en",
                    "script": "Latn",
                    "format": "text / plain",
                }
            ],
            "docid": [{"id": "ref_01", "type": "test_dataset_01"}],
            "formattedref": {
                "content": "BCP4",
                "language": "en",
                "script": "Latn",
                "format": "text/plain",
            },
            "relation": [
                {
                    "type": "includes",
                    "bibitem": {
                        "id": "test_id",
                        "title": [
                            {
                                "content": "title",
                                "language": "en",
                                "script": "Latn",
                                "format": "text / plain",
                            }
                        ],
                        "link": [
                            {
                                "content": "https://raw.githubusercontent.com/relaton/relaton-data-ietf/master/data/reference.RFC"
                                ".1917.xml",
                                "type": "xml",
                            }
                        ],
                        "type": "standard",
                        "docid": [{"id": "RFC1917", "type": "RFC"}],
                        "docnumber": "RFC1917",
                        "date": [{"type": "published", "value": "1996-02"}],
                        "contributor": [
                            self.contributor_organization_data,
                            self.contributor_person_data,
                        ],
                    },
                }
            ],
        }

        self.bibitem = BibliographicItem(**self.bibitem_data)
        self.contributor_organization = Contributor(
            **self.contributor_organization_data
        )
        self.contributor_person = Contributor(**self.contributor_person_data)

    def test_bibliographicitem_to_xml(self):
        # TODO validate XML schema
        to_xml(self.bibitem)

    def test_fail_bibliographicitem_to_xml_if_wrong_combination_of_titles_and_relations(
        self,
    ):
        data = copy(self.bibitem_data)
        del data["title"]
        del data["relation"]
        new_bibitem_with_missing_data = BibliographicItem(**data)
        with self.assertRaises(ValueError):
            to_xml(new_bibitem_with_missing_data)

    def test_create_reference(self):
        # TODO validate XML schema
        ref = create_reference(self.bibitem)
        self.assertEqual(ref.tag, "reference")

    def test_fail_create_reference_if_missing_titles(self):
        data = copy(self.bibitem_data)
        del data["title"]
        new_bibitem_with_missing_data = BibliographicItem(**data)
        with self.assertRaises(ValueError):
            create_reference(new_bibitem_with_missing_data)

    def test_create_author(self):
        # TODO validate XML schema
        author = create_author(self.contributor_organization)
        create_author(self.contributor_person)
        self.assertEqual(author.tag, "author")

    def test_fail_create_author_if_incompatible_roles(self):
        contributor_organization = copy(self.contributor_organization)
        contributor_person = copy(self.contributor_person)
        contributor_organization.role = None
        contributor_person.role = None
        with self.assertRaises(ValueError):
            create_author(contributor_organization)
            create_author(contributor_person)

    def test_fail_create_author_if_missing_person_or_organization(self):
        contributor_organization = copy(self.contributor_organization)
        contributor_person = copy(self.contributor_person)
        contributor_organization.organization = None
        contributor_person.person = None
        with self.assertRaises(ValueError):
            create_author(contributor_organization)
            create_author(contributor_person)
