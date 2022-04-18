import os
from copy import copy
from io import StringIO

from django.test import TestCase
from lxml import etree

from bib_models import BibliographicItem, Contributor, DocID, Link
from xml2rfc_compat.serializer import to_xml, create_reference, create_author, get_suitable_anchor, get_suitable_target, \
    extract_doi_series, extract_rfc_series, extract_id_series, extract_w3c_series, extract_3gpp_tr_series, \
    extract_ieee_series


class XML2RFCSerializersTestCase(TestCase):
    """
    Test cases for serializers.py file
    """

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
        """
        Test that a BibliographicItem is properly converted to XML.
        Validate the XML formatting against an XSD schema.
        The XSD schema was generated using trang using the official
        Relax NG schema.
        See issue https://github.com/ietf-ribose/bibxml-service/issues/155
        for more details.
        """

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
        """
        to_xml should fail if no titles or relations are present.
        """
        data = copy(self.bibitem_reference_data)
        del data["title"]
        new_bibitem_with_missing_data = BibliographicItem(**data)
        with self.assertRaises(ValueError):
            to_xml(new_bibitem_with_missing_data)

    def test_create_reference(self):
        ref = create_reference(self.bibitem_reference)
        self.assertEqual(ref.tag, "reference")

    def test_fail_create_reference_if_missing_titles(self):
        """
        create_reference should fail if no title is present.
        """
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
        """
        create_author should fail if no person or organization has a role.
        """
        contributor_organization = copy(self.contributor_organization)
        contributor_person = copy(self.contributor_person)
        contributor_organization.role = None
        contributor_person.role = None
        with self.assertRaises(ValueError):
            create_author(contributor_organization)
            create_author(contributor_person)

    def test_fail_create_author_if_missing_person_or_organization(self):
        """
        create_author should fail if no person or organization is present.
        """
        contributor_organization = copy(self.contributor_organization)
        contributor_person = copy(self.contributor_person)
        contributor_organization.organization = None
        contributor_person.person = None
        with self.assertRaises(ValueError):
            create_author(contributor_organization)
            create_author(contributor_person)

    def test_get_suitable_anchor(self):
        id = "RFC1918"
        docids = [DocID(id=id, type="RFC", scope="anchor")]
        anchor = get_suitable_anchor(docids)
        self.assertIsInstance(anchor, str)
        self.assertEqual(anchor, id)

    def test_get_suitable_anchor_without_scope_with_primary(self):
        """
        get_suitable_anchor should return DocID.id if primary=True and
        DocID.scope is not present or DocID.scope != "anchor"
        """
        id = "RFC1918"
        docids = [DocID(id=id, type="RFC", primary=True)]
        anchor = get_suitable_anchor(docids)
        self.assertIsInstance(anchor, str)
        self.assertEqual(anchor, id)

        docids = [DocID(id=id, type="RFC", scope="no_anchor")]
        anchor = get_suitable_anchor(docids)
        self.assertIsInstance(anchor, str)
        self.assertEqual(anchor, id)

    def test_fail_get_suitable_anchor(self):
        """
        get_suitable_anchor should fail if a list of empty ids is provided
        """
        docids = []
        with self.assertRaises(ValueError):
            get_suitable_anchor(docids)

    def test_get_suitable_target(self):
        link_content = "link_content"
        links = [Link(content=link_content, type="src"),
                 Link(content="not_src_link", type="not_src")]
        target_content = get_suitable_target(links)
        self.assertIsInstance(target_content, str)
        self.assertEqual(target_content, link_content)

    def test_get_suitable_target_non_src_link(self):
        """
        get_suitable_target should return the link content if Link.type != "src"
        """
        link_content = "not_src_link"
        links = [Link(content=link_content, type="not_src")]
        target_content = get_suitable_target(links)
        self.assertIsInstance(target_content, str)
        self.assertEqual(target_content, link_content)

    def test_fail_get_suitable_target(self):
        """
        get_suitable_target should fail if a list of empty links is provided
        """
        links = []
        with self.assertRaises(ValueError):
            get_suitable_target(links)

    def test_extract_doi_series(self):
        id_value = "10.17487/RFC4036"
        docid = DocID(id=id_value, type="DOI")
        type, id = extract_doi_series(docid)
        self.assertEqual(type, "DOI")
        self.assertEqual(id, id_value)

    def test_fail_extract_doi_series(self):
        """
        extract_doi_series should fail with the wrong combination
        of id and type.
        """
        id_value = "10.17487/RFC4036"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_doi_series(docid))

    def test_extract_rfc_series(self):
        id_value = "RFC 4036"
        docid = DocID(id=id_value, type="IETF")
        serie, id = extract_rfc_series(docid)
        self.assertEqual(serie, "RFC")
        self.assertEqual(id, id_value.split(" ")[-1])

    def test_fail_extract_rfc_series(self):
        """
        extract_rfc_series should fail with the wrong combination
        of id and type.
        """
        id_value = "RFC 4036"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_rfc_series(docid))

    def test_extract_id_series(self):
        id_value = "draft-ietf-hip-rfc5201-bis-13"
        type_value = "Internet-Draft"
        docid = DocID(id=id_value, type=type_value)
        serie, id = extract_id_series(docid)
        self.assertEqual(serie, type_value)
        self.assertEqual(id, id_value)

    def test_fail_extract_id_series(self):
        """
        extract_id_series should fail with the wrong combination
        of id and type.
        """
        id_value = "draft-ietf-hip-rfc5201-bis-13"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_id_series(docid))

    def test_extract_w3c_series(self):
        id_value = "W3C REC-owl2-syntax-20121211"
        type_value = "W3C"
        docid = DocID(id=id_value, type=type_value)
        serie, id = extract_w3c_series(docid)
        self.assertEqual(serie, type_value)
        self.assertEqual(id, id_value.split('W3C ')[-1])

    def test_fail_extract_w3c_series(self):
        """
        extract_w3c_series should fail with the wrong combination
        of id and type.
        """
        id_value = "W3C REC-owl2-syntax-20121211"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_w3c_series(docid))

    def test_extract_3gpp_tr_series(self):
        id_value = "3GPP TR 25.321:Rel-8/8.3.0"
        type_value = "3GPP"
        docid = DocID(id=id_value, type=type_value)
        serie, id = extract_3gpp_tr_series(docid)
        self.assertEqual(serie, f"{type_value} TR")
        self.assertEqual(id, f"{id_value.split('3GPP TR ')[1].split(':')[0]} {id_value.split('/')[-1]}")

    def test_fail_extract_3gpp_tr_series(self):
        """
        extract_3gpp_tr_series should fail with the wrong combination
        of id and type.
        """
        id_value = "3GPP TR 25.321:Rel-8/8.3.0"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_3gpp_tr_series(docid))

    def test_extract_ieee_series(self):
        id_value = "IEEE P2740/D-6.5.2020-08"
        type_value = "IEEE"
        docid = DocID(id=id_value, type=type_value)
        serie, id = extract_ieee_series(docid)
        id_value_alternative, year, *_ = docid.id.split(' ')[-1].lower().strip().split('.')
        self.assertEqual(serie, type_value)
        self.assertTrue(id == '%s-%s' % (id_value_alternative.replace('-', '.'), year) or id == id_value)

    def test_fail_extract_ieee_series(self):
        """
        extract_ieee_series should fail with the wrong combination
        of id and type.
        """
        id_value = "IEEE P2740/D-6.5.2020-08"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_ieee_series(docid))
