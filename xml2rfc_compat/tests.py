import os
from copy import copy
from io import StringIO

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
        self.bibitem_reference_data = {
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
            "contributor": [self.contributor_person_data],
            "date": [{"type": "published", "value": "1996-02"}],
        }

        self.bibitem_referencegroup_data = {
            "id": "ref_02",
            "docid": [{"id": "ref_02", "type": "test_dataset_02"}],
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
                        "contributor": [
                            self.contributor_organization_data,
                            self.contributor_person_data,
                        ],
                        "link": [
                            {
                                "content": "https://raw.githubusercontent.com/relaton/relaton-data-ietf/master/data/reference.RFC"
                                ".1918.xml",
                                "type": "xml",
                            }
                        ],
                        "type": "standard",
                        "docid": [{"id": "RFC1918", "type": "RFC"}],
                        "docnumber": "RFC1918",
                        "date": [{"type": "published", "value": "1998-02"}],
                    },
                }
            ],
        }

        self.bibitem_reference = BibliographicItem(**self.bibitem_reference_data)
        self.bibitem_referencegroup = BibliographicItem(
            **self.bibitem_referencegroup_data
        )
        self.contributor_organization = Contributor(
            **self.contributor_organization_data
        )
        self.contributor_person = Contributor(**self.contributor_person_data)

    def test_bibliographicitem_to_xml(self):

        xml_reference = to_xml(self.bibitem_reference)
        xml_referencegroup = to_xml(self.bibitem_referencegroup)

        module_dir = os.path.dirname(__file__)
        file_path = os.path.join(module_dir, "static/schemas/v3.xsd")
        xmlschema = etree.XMLSchema(file=file_path)

        xmlschema.assertValid(xml_reference)
        xmlschema.assertValid(xml_referencegroup)

    def test_fail_bibliographicitem_to_xml_if_wrong_combination_of_titles_and_relations(
        self,
    ):
        data = copy(self.bibitem_reference_data)
        del data["title"]
        new_bibitem_with_missing_data = BibliographicItem(**data)
        with self.assertRaises(ValueError):
            to_xml(new_bibitem_with_missing_data)

    def test_create_reference(self):
        ref = create_reference(self.bibitem_reference)
        self.assertEqual(ref.tag, "reference")

    def test_fail_create_reference_if_missing_titles(self):
        data = copy(self.bibitem_reference_data)
        del data["title"]
        new_bibitem_with_missing_data = BibliographicItem(**data)
        with self.assertRaises(ValueError):
            create_reference(new_bibitem_with_missing_data)

    def test_create_author(self):
        author_xsd = StringIO(
            """
            <xsd:schema attributeFormDefault="unqualified" elementFormDefault="qualified" 
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"> 
                <xsd:element name="author" type="authorType"/> 
                <xsd:complexType name="authorType"> 
                    <xsd:sequence> 
                        <xsd:element type="xsd:string" name="organization"/> 
                    </xsd:sequence> 
                </xsd:complexType> 
            </xsd:schema> 
            """
        )
        xmlschema_doc = etree.parse(author_xsd)
        author_xmlschema = etree.XMLSchema(xmlschema_doc)

        author_organization = create_author(self.contributor_organization)
        author_person = create_author(self.contributor_person)
        self.assertEqual(author_organization.tag, "author")
        self.assertEqual(author_person.tag, "author")

        author_xmlschema.validate(author_organization)
        author_xmlschema.validate(author_person)

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
