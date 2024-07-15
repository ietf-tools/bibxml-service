import os
from copy import copy
from io import StringIO
from typing import Dict, List, Any, cast
from unittest import TestCase

from lxml import etree
from lxml.etree import _Element

from relaton.models import (
    BibliographicItem,
    Contributor,
    DocID,
    Link,
    GenericStringValue,
)
from relaton.models.bibitemlocality import LocalityStack, Locality
from ..serializers import serialize
from ..serializers.abstracts import (
    create_abstract,
    get_paragraphs,
    get_paragraphs_html,
    get_paragraphs_jats,
)
from ..serializers.anchor import get_suitable_anchor
from ..serializers.authors import create_author, is_rfc_publisher, filter_contributors
from ..serializers.reference import build_refcontent_string, create_reference, filter_docids
from ..serializers.series import (
    extract_doi_series,
    extract_rfc_series,
    extract_id_series,
    extract_w3c_series,
    extract_3gpp_tr_series,
    extract_ieee_series,
)
from ..serializers.target import get_suitable_target


class SerializerTestCase(TestCase):
    def setUp(self):
        # Data for a Contributor (AKA Author) of type Organization
        contributor_organization_data: Dict[str, Any] = {
            "organization": {
                "name": {
                    "content": "Internet Engineering Task Force",
                    "language": "en",
                },
                "abbreviation": {"content": "abbr", "language": "en"},
            },
            "role": [{
                "type": "publisher",
            }],
        }
        self.contributor_organization = \
            Contributor(**contributor_organization_data)

        # Data for a Contributor (AKA Author) of type Person
        self.contributor_person_data: Dict[str, Any] = {
            "person": {
                "name": {
                    "given": {
                        "formatted_initials": {
                            "content": "Mr",
                            "language": "en",
                        },
                    },
                    "surname": {"content": "Cerf", "language": "en"},
                    "completename": {"content": "Mr Cerf", "language": "en"},
                },
            },
            "role": [{
                "type": "author",
            }],
        }
        self.contributor_person = Contributor(**self.contributor_person_data)

        # Data for a BibliographicItem which will be converted
        # to a <reference> root tag in the XML output
        self.bibitem_reference_data: Dict[str, Any] = {
            "id": "ref_01",
            "title": [
                {
                    "content": "title",
                    "language": "en",
                    "script": "Latn",
                    "format": "text / plain",
                }
            ],
            "docid": [
                {"id": "ref_01", "scope": "anchor", "type": "type"},
                {"id": "IEEE P2740/D-6.5 2020-08", "type": "IEEE"},
            ],
            "contributor": [self.contributor_person_data],
            "date": [{"type": "published", "value": "1996-02-11"}],
            "abstract": [{"content": "abstract_content"}],
            "series": [{"title": ["IEEE P2740/D-6.5 2020-08"], "type": "IEEE"}],
            "version": [{"draft": True}],
            "extent": {"locality": [
                {"type": "container-title", "reference_from": "Container Title"},
                {"type": "volume", "reference_from": "1"},
                {"type": "issue", "reference_from": "2"},
                {"type": "page", "reference_from": "3"}
            ]}
        }
        self.bibitem_reference = \
            BibliographicItem(**self.bibitem_reference_data)

        # Data for a BibliographicItem which will be converted
        # to a <referencegroup> root tag in the XML output
        self.bibitem_referencegroup_data: Dict[str, Any] = {
            "id": "ref_02",
            "docid": [{"id": "ref_02", "type": "test_dataset_02"}],
            "link": {
                "content": "https://www.rfc-editor.org/info/std94",
                "type": "src"
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
                        "contributor": [
                            contributor_organization_data,
                            self.contributor_person_data,
                        ],
                        "link": [
                            {
                                "content": "https://raw.githubusercontent.com/relaton/relaton-data-ietf/master/data"
                                "/reference.RFC"
                                ".1918.xml",
                                "type": "xml",
                            }
                        ],
                        "type": "standard",
                        "docid": [{"id": "RFC1918", "type": "RFC"}],
                        "docnumber": "RFC1918",
                        "date": [{"type": "published", "value": "1998-02-11"}],
                        "extent": {"locality": [
                            {"type": "container-title", "reference_from": "Container Title"},
                            {"type": "volume", "reference_from": "1"},
                            {"type": "issue", "reference_from": "2"},
                            {"type": "page", "reference_from": "3"}
                        ]}
                    },
                }
            ],
        }
        self.bibitem_referencegroup = BibliographicItem(
            **self.bibitem_referencegroup_data
        )

        module_dir = os.path.dirname(__file__)
        file_path = os.path.join(module_dir, "static/schemas/v3.xsd")
        self.xmlschema = etree.XMLSchema(file=file_path)

    def test_bibliographicitem_to_xml(self):
        """
        Test that a BibliographicItem is properly converted to XML,
        and that its format validates against a converted authoritative
        schema (xml2rfc_compat/tests/static/v3.xsd).
        More info about the schema here
        https://github.com/ietf-ribose/bibxml-service/issues/155
        """

        xml_reference = serialize(self.bibitem_reference)
        xml_referencegroup = serialize(self.bibitem_referencegroup)

        module_dir = os.path.dirname(__file__)
        file_path = os.path.join(module_dir, "static/schemas/v3.xsd")
        xmlschema = etree.XMLSchema(file=file_path)

        xmlschema.assertValid(xml_reference)
        xmlschema.assertValid(xml_referencegroup)

    def test_target_referencegroup(self):
        """
        Target should be set as attribute of <referencegroup>.
        """
        xml_referencegroup = serialize(self.bibitem_referencegroup)
        target = xml_referencegroup.keys()[1]
        self.assertEqual(target, "target")
        self.assertEqual(
            xml_referencegroup.get(target),
            self.bibitem_referencegroup_data["link"]["content"]
        )

    def test_build_refcontent_string(self):
        """
        Test build_refcontent_string returns a valid XML output.
        Test that schema is valid and that output content
        matches the input.

        A valid reference output looks like:
        <reference anchor="ref_01">
            <front>
                <title py:pytype="str">title</title>
                <author fullname="Mr Cerf" surname="Cerf" initials="Mr"/>
                <date year="1996" month="February"/>
                <abstract>
                    <t>abstract_content</t>
                </abstract>
            </front>
            <refcontent>Ref Content</refcontent>
            <seriesInfo name="IEEE" value="IEEE P2740/D-6.5 2020-08"/>
        </reference>
        """
        reference = create_reference(self.bibitem_reference)
        self.assertEqual(reference.tag, "reference")
        anchor = reference.keys()[0]
        self.assertEqual(anchor, "anchor")
        self.assertEqual(
            reference.get(anchor), self.bibitem_reference_data["docid"][0]["id"]
        )

        # <front> element
        front = reference.getchildren()[0]
        self.assertEqual(front.tag, "front")

        # <title> element
        title = front.getchildren()[0]
        self.assertEqual(title.tag, "title")
        self.assertEqual(title.text, self.bibitem_reference_data["title"][0]["content"])

        # <author> element
        author = front.getchildren()[1]
        self.assertEqual(author.tag, "author")
        self.assertEqual(author.keys()[0], "fullname")
        self.assertEqual(author.keys()[1], "surname")
        self.assertEqual(author.keys()[2], "initials")
        self.assertEqual(
            author.get(author.keys()[0]),
            self.contributor_person_data["person"]["name"]["completename"]["content"],
        )
        self.assertEqual(
            author.get(author.keys()[1]),
            self.contributor_person_data["person"]["name"]["surname"]["content"],
        )
        self.assertEqual(
            author.get(author.keys()[2]),
            self.contributor_person_data["person"]["name"]["given"]["formatted_initials"]["content"],
        )

        # <date> element
        date = front.getchildren()[2]
        self.assertEqual(date.tag, "date")

        self.assertEqual(date.keys()[0], "year")
        self.assertEqual(date.keys()[1], "month")
        self.assertEqual(
            date.get(date.keys()[0]),
            self.bibitem_reference_data["date"][0]["value"].split("-")[0],
        )

        # <abstract> element
        abstract = front.getchildren()[3]
        self.assertEqual(abstract.tag, "abstract")
        self.assertEqual(
            abstract.getchildren()[0],
            self.bibitem_reference_data["abstract"][0]["content"],
        )

        # <refcontent> element
        refcontent = reference.getchildren()[1]
        self.assertEqual(
            refcontent,
            f"{self.bibitem_reference_data['extent']['locality'][0]['reference_from']}, "
            f"vol. {self.bibitem_reference_data['extent']['locality'][1]['reference_from']}, "
            f"no. {self.bibitem_reference_data['extent']['locality'][2]['reference_from']}, "
            f"pp. {self.bibitem_reference_data['extent']['locality'][3]['reference_from']}"
        )

    def test_build_refcontent_string_with_date_type_different_than_published(self):
        """
        build_refcontent_string should create a <date> tag using the date with
        type == 'published'. If no date is of this type, it should choose
        a random date between the ones provided.
        """
        data = copy(self.bibitem_reference_data)
        data["date"][0]["type"] = "random_type"
        new_bibitem = BibliographicItem(**data)
        reference = create_reference(new_bibitem)
        date = reference.getchildren()[0].getchildren()[2]
        self.assertTrue(any(
            element in ["year", "month", "day"]
            for element in reference.getchildren()[0].getchildren()[2].keys()
        ))
        self.assertEqual(
            date.get(date.keys()[0]), data["date"][0]["value"].split("-")[0]
        )

    def test_create_reference_for_IANA_entries_should_not_include_dates(self):
        data = copy(self.bibitem_reference_data)
        data["docid"][0]["type"] = "IANA"
        new_bibitem = BibliographicItem(**data)
        reference = create_reference(new_bibitem)
        self.assertFalse(any(
            element not in ["year", "month", "day"]
            for element in reference.getchildren()[0].getchildren()[2].keys()
        ))

    def test_build_refcontent_string_with_localitystack(self):
        title = "Container Title"
        volume = "1"
        issue = "2"
        page = "3"
        extent = LocalityStack(locality=[
            Locality(type="container-title", reference_from=title),
            Locality(type="volume", reference_from=volume),
            Locality(type="issue", reference_from=issue),
            Locality(type="page", reference_from=page),

        ])
        refcontent = build_refcontent_string(extent)
        self.assertEqual(
            refcontent,
            f"{title}, vol. {volume}, no. {issue}, pp. {page}")

    def test_build_refcontent_string_with_locality(self):
        title = "Container Title"
        extent = Locality(type="container-title", reference_from=title)

        refcontent = build_refcontent_string(extent)
        self.assertEqual(refcontent, f"{title}")

    def test_filter_contributors(self):
        contribs_data: Dict[str, Any] = {
            "organization": {
                "name": {"content": "RFC Publisher", "language": "en"},
            },
            "role": [{
                "type": "publisher",
            }],
        }
        contribs = [Contributor(**contribs_data)]
        self.assertEqual(filter_contributors(contribs), [])
        contribs_data["organization"]["name"]["content"] = "Not RFC Publisher"
        contribs = [Contributor(**contribs_data)]
        self.assertEqual(len(filter_contributors(contribs)), 1)

    def test_create_author(self):
        """
        create_author should return a valid XML.
        The XML should validate against an
        authoritative schema.
        """
        author_xsd = StringIO(
            """
            <xsd:schema attributeFormDefault="unqualified"
            elementFormDefault="qualified"
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
        contributor_organization.role = []
        contributor_person.role = []
        with self.assertRaises(ValueError):
            create_author(contributor_organization)
        with self.assertRaises(ValueError):
            create_author(contributor_person)

    def test_fail_create_author_if_missing_person_or_organization(self):
        """
        create_author should fail if no person or organization is provided
        """
        contributor_organization = copy(self.contributor_organization)
        contributor_person = copy(self.contributor_person)
        contributor_organization.organization = None
        contributor_person.person = None
        with self.assertRaises(ValueError):
            create_author(contributor_organization)
        with self.assertRaises(ValueError):
            create_author(contributor_person)

    def test_create_author_IANA_entries(self):
        """
        create_author should remove the abbreviation
        property for Internet Assigned Numbers Authority
        entries and abbreviate its value to IANA.
        <organization>IANA</organization>
        """
        contributor_organization_data: Dict[str, Any] = {
            "organization": {
                "name": {
                    "content": "Internet Assigned Numbers Authority",
                    "language": "en",
                },
                "abbreviation": {"content": "IANA", "language": "en"},
            },
            "role": [{
                "type": "publisher",
            }],
        }
        author_organization = \
            create_author(Contributor(**contributor_organization_data))
        self.assertEqual(author_organization.tag, "author")
        if els := author_organization.xpath("//organization"):
            # TODO: Are we sure xpath() returns a list of strings not elements?
            self.assertEqual(cast(List[str], els)[0], "IANA")
        else:
            raise AssertionError("xpath returned no organization")

    def test_create_author_non_IANA_entries(self):
        """
        create_author should return the full-length name
        of the organization within the <organization> tag
        """
        organization_name = "Any Organization"
        contributor_organization_data: Dict[str, Any] = {
            "organization": {
                "name": {"content": organization_name, "language": "en"},
                "abbreviation": {"content": "NONIANA", "language": "en"},
            },
            "role": [{
                "type": "publisher",
            }],
        }
        author_organization = \
            create_author(Contributor(**contributor_organization_data))
        self.assertEqual(author_organization.tag, "author")
        if els := author_organization.xpath("//organization"):
            # TODO: Are we sure xpath() returns a list of strings not elements?
            self.assertEqual(cast(List[str], els)[0], organization_name)
        else:
            raise AssertionError("xpath returned no organization")

    def test_create_author_with_editor_role(self):
        """
        create_author should return an Author element with attribute
        role == editor if Contributor.role is set to editor
        """
        contributor_editor: Dict[str, Any] = {
            "organization": {
                "name": {"content": "name", "language": "en"},
            },
            "role": [{
                "type": "editor",
            }],
        }
        author_organization = create_author(Contributor(**contributor_editor))
        self.assertEqual(author_organization.tag, "author")
        self.assertEqual(author_organization.get("role"), "editor")

    def test_create_author_with_non_editor_role(self):
        """
        create_author should return an Author element with attribute
        role != editor if Contributor.role is set to something else
        then editor
        """
        contributor_editor: Dict[str, Any] = {
            "organization": {
                "name": {"content": "name", "language": "en"},
            },
            "role": [{
                "type": "publisher",
            }],
        }
        author_organization = create_author(Contributor(**contributor_editor))
        self.assertEqual(author_organization.tag, "author")
        self.assertNotEqual(author_organization.get("role"), "editor")

    def test_create_author_affiliation(self):
        person: dict[str, Any] = {
            "person": {
                "name": {
                    "completename": {"content": "Dr Cerf", "language": "en"},
                },
                "affiliation": {
                    "organization": {
                        "name": {
                            "content": "Internet Engineering Task Force",
                            "language": "en",
                        },
                    }
                },
            },
            "role": [
                {
                    "type": "author",
                }
            ],
        }
        author: _Element = create_author(Contributor(**person))
        self.assertEqual(author.organization, "Internet Engineering Task Force")

    def test_create_author_affiliations(self):
        person: dict[str, Any] = {
            "person": {
                "name": {
                    "completename": {"content": "Dr Cerf", "language": "en"},
                },
                "affiliation": [
                    {
                        "organization": {
                            "name": {
                                "content": "Internet Research Task Force",
                                "language": "en",
                            },
                        }
                    },
                    {
                        "organization": {
                            "name": {
                                "content": "Internet Engineering Task Force",
                                "language": "en",
                            },
                        }
                    },
                ],
            },
            "role": [
                {
                    "type": "author",
                }
            ],
        }
        author: _Element = create_author(Contributor(**person))
        self.assertEqual(author.organization, "Internet Research Task Force")

    def test_create_author_org_address(self):
        org: dict[str, Any] = {
            "organization": {
                "name": {
                    "content": "Internet Engineering Task Force",
                    "language": "en",
                },
                "contact": [
                    {"address": {"country": "United States", "city": "Santa Cruz"}},
                    {"address": {"country": "United States"}},
                ],
                "url": "www.ietf.org",
            },
            "role": [
                {
                    "type": "publisher",
                }
            ],
        }
        author: _Element = create_author(Contributor(**org))
        self.assertTrue(hasattr(author, "address"))
        self.assertTrue(hasattr(author.address, "postal"))
        self.assertTrue(hasattr(author.address.postal, "country"))
        self.assertEqual(author.address.postal.country, "United States")
        self.assertTrue(hasattr(author.address.postal, "city"))
        self.assertEqual(author.address.postal.city, "Santa Cruz")
        self.assertTrue(hasattr(author.address, "uri"))
        self.assertEqual(author.address.uri, "www.ietf.org")

    def test_create_author_missing_complete_name(self):
        person: dict[str, Any] = {
            "person": {
                "name": {
                    "prefix": {"content": "Dr", "language": "en"},
                    "given": {
                        "formatted_initials": {"content": "V G.", "language": "en"}
                    },
                    "surname": {"content": "Cerf", "language": "en"},
                },
            },
            "role": [
                {
                    "type": "author",
                }
            ],
        }
        author: _Element = create_author(Contributor(**person))
        self.assertEqual(author.get("fullname"), "Dr V G.Cerf")

    def test_is_rfc_publisher(self):
        contributor_editor: Dict[str, Any] = {
            "organization": {
                "name": {"content": "RFC Publisher", "language": "en"},
            },
            "role": [{
                "type": "publisher",
            }],
        }
        self.assertTrue(is_rfc_publisher(Contributor(**contributor_editor)))
        contributor_editor["organization"]["name"]["content"] = "Not RFC Publisher"
        self.assertFalse(is_rfc_publisher(Contributor(**contributor_editor)))

    def test_get_suitable_anchor(self):
        """
        get_suitable_anchor should return the correct anchor value
        """
        anchor = get_suitable_anchor(self.bibitem_reference)
        self.assertIsInstance(anchor, str)
        self.assertEqual(
            anchor,
            next(
                docid.id
                for docid in self.bibitem_reference.docid
                if docid.scope == "anchor"
            ),
        )

    def test_get_suitable_anchor_without_scope_with_primary(self):
        """
        get_suitable_anchor should return DocID.id if primary=True and
        DocID.scope is not provided or DocID.scope != "anchor"
        """
        bibitem_with_primary_docid = copy(self.bibitem_reference)
        bibitem_with_primary_docid.docid[0].primary = True
        bibitem_with_primary_docid.docid[0].scope = None

        anchor = get_suitable_anchor(bibitem_with_primary_docid)
        self.assertIsInstance(anchor, str)
        self.assertEqual(
            anchor,
            next(
                docid.id
                for docid in bibitem_with_primary_docid.docid
                if docid.primary
            ),
        )

        bibitem_with_no_scope = copy(self.bibitem_reference)
        bibitem_with_no_scope.docid[0].scope = "no_scope"
        anchor = get_suitable_anchor(bibitem_with_no_scope)
        self.assertIsInstance(anchor, str)
        self.assertEqual(
            anchor,
            next(
                docid.id
                for docid in bibitem_with_no_scope.docid
                if docid.scope == "no_scope"
            ),
        )

    def test_fail_get_suitable_anchor(self):
        """
        get_suitable_anchor should fail if BibliographicItem.docid == []
        """
        self.bibitem_reference.docid = []
        with self.assertRaises(ValueError):
            get_suitable_anchor(self.bibitem_reference)

    def test_get_suitable_target(self):
        """
        get_suitable_target should return the content of the
        Link whose type == "src"
        """
        link_content = "link_content"
        links = [
            Link(content=link_content, type="src"),
            Link(content="not_src_link", type="not_src"),
        ]
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
        get_suitable_target should fail if called with
        a list of empty links
        """
        links: List[Any] = []
        with self.assertRaises(ValueError):
            get_suitable_target(links)

    def test_extract_doi_series(self):
        """
        extract_doi_series should return the correct
        type and id values
        """
        id_value = "10.17487/RFC4036"
        docid = DocID(id=id_value, type="DOI")
        if result := extract_doi_series(docid):
            type, id = result
            self.assertEqual(type, "DOI")
            self.assertEqual(id, id_value)
        else:
            raise AssertionError("Failed to extract DOI series")

    def test_fail_extract_doi_series(self):
        """
        extract_doi_series should fail with the wrong combination
        of DocID.id and DocID.type.
        """
        id_value = "10.17487/RFC4036"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_doi_series(docid))

    def test_extract_rfc_series(self):
        """
        extract_rfc_series should return the correct
        serie and id values
        """
        id_value = "RFC 4036"
        docid = DocID(id=id_value, type="IETF")
        if result := extract_rfc_series(docid):
            series, id = result
            self.assertEqual(series, "RFC")
            self.assertEqual(id, id_value.split(" ")[-1])
        else:
            raise AssertionError("Failed to extract RFC series")

    def test_fail_extract_rfc_series(self):
        """
        extract_rfc_series should fail with the wrong combination
        of DocID.id and DocID.type.
        """
        id_value = "RFC 4036"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_rfc_series(docid))

    def test_extract_id_series(self):
        """
        extract_id_series should return the correct
        type and id values
        """
        id_value = "draft-ietf-hip-rfc5201-bis-13"
        type_value = "Internet-Draft"
        docid = DocID(id=id_value, type=type_value)
        if result := extract_id_series(docid):
            series, id = result
            self.assertEqual(series, type_value)
            self.assertEqual(id, id_value)
        else:
            raise AssertionError("Failed to extract ID series")

    def test_fail_extract_id_series(self):
        """
        extract_id_series should fail with the wrong combination
        of DocID.id and DocID.type.
        """
        id_value = "draft-ietf-hip-rfc5201-bis-13"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_id_series(docid))

    def test_extract_w3c_series(self):
        """
        extract_w3c_series should return the correct
        type and id values
        """
        id_value = "W3C.REC-owl2-syntax-20121211"
        type_value = "W3C"
        docid = DocID(id=id_value, type=type_value)
        if result := extract_w3c_series(docid):
            series, id = result
            self.assertEqual(series, type_value)
            self.assertEqual(id, id_value.replace(".", " ").split("W3C ")[-1])
        else:
            raise AssertionError("Failed to extract W3C series")

    def test_fail_extract_w3c_series(self):
        """
        extract_w3c_series should fail with the wrong combination
        of DocID.id and DocID.type.
        """
        id_value = "W3C REC-owl2-syntax-20121211"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_w3c_series(docid))

    def test_extract_3gpp_tr_series(self):
        """
        extract_3gpp_tr_series should return the correct
        type and id values
        """
        id_value = "3GPP TR 25.321:Rel-8/8.3.0"
        type_value = "3GPP"
        docid = DocID(id=id_value, type=type_value)
        if result := extract_3gpp_tr_series(docid):
            series, id = result
            self.assertEqual(series, f"{type_value} TR")
            self.assertEqual(
                id,
                f"{id_value.split('3GPP TR ')[1].split(':')[0]} "
                f"{id_value.split('/')[-1]}",
            )
        else:
            raise AssertionError("Failed to extract 3GPP series")

    def test_fail_extract_3gpp_tr_series(self):
        """
        extract_3gpp_tr_series should fail with the wrong combination
        of DocID.id and DocID.type.
        """
        id_value = "3GPP TR 25.321:Rel-8/8.3.0"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_3gpp_tr_series(docid))

    def test_extract_ieee_series(self):
        """
        extract_ieee_series should return the correct
        type and id values
        """
        id_value = "IEEE P2740/D-6.5.2020-08"
        type_value = "IEEE"
        docid = DocID(id=id_value, type=type_value)
        if result := extract_ieee_series(docid):
            series, id = result
            id_value_alternative, year, *_ = (
                docid.id.split(" ")[-1].lower().strip().split(".")
            )
            self.assertEqual(series, type_value)
            self.assertTrue(id == "%s-%s" % (
                id_value_alternative.replace("-", "."),
                year,
            ))
        else:
            raise AssertionError("Failed to extract IEEE series")

    def test_extract_ieee_series_with_malformed_id(self):
        """
        extract_ieee_series should return DocID.id if id_value is not
        formatted properly (e.g. right format "IEEE P2740/D-6.5.2020-08").
        """
        id_value = "IEEE P2740/D-6.5 2020-08"
        type_value = "IEEE"
        docid = DocID(id=id_value, type=type_value)
        if result := extract_ieee_series(docid):
            series, id = result
            self.assertEqual(series, type_value)
            self.assertEqual(id, id_value)
        else:
            raise AssertionError(
                "Failed to extract IEEE series with malformed ID")

    def test_fail_extract_ieee_series(self):
        """
        extract_ieee_series should fail with the wrong combination
        of DocID.id and DocID.type.
        """
        id_value = "IEEE P2740/D-6.5.2020-08"
        docid = DocID(id=id_value, type="TYPE")
        self.assertIsNone(extract_ieee_series(docid))

    def test_create_abstract(self):
        """
        create_abstract should return the content in English (en or eng)
        if present or any other content otherwise (normally the first
        of the list)
        """
        abstracts: List[GenericStringValue] = [
            GenericStringValue(
                content="content",
                format="text/html",
                language="en"),
            GenericStringValue(
                content="contenuto",
                format="text/html",
                language="it"),
        ]

        abstract = create_abstract(abstracts)
        self.assertEqual(
            list(abstract.iterchildren())[0],
            next(
                abstract.content
                for abstract in abstracts
                if abstract.language == "en"
            ),
        )
        self.assertEqual(abstract.tag, "abstract")

    def test_fail_create_abstract(self):
        """
        create_abstract should fail if called with a list
        of empty abstracts
        """
        abstracts: List[GenericStringValue] = []
        with self.assertRaises(ValueError):
            create_abstract(abstracts)

    def test_get_paragraphs(self):
        """
        get_paragraphs should return the right content based on
        the paragraph format (HTML, JATS or plain text)
        """
        html_content = "HTML"
        html_paragraph = GenericStringValue(
            content=f"<p>{html_content}</p>", format="text/html"
        )
        paragraph = get_paragraphs(html_paragraph)
        self.assertEqual(paragraph[0], html_content)

        jats_content = "JATS"
        jats_paragraph = GenericStringValue(
            content=f"<jats:p>{jats_content}</jats:p>",
            format="application/x-jats+xml"
        )
        paragraph = get_paragraphs(jats_paragraph)
        self.assertEqual(paragraph[0], jats_content)

        invalid_content = "invalid"
        invalid_paragraph = GenericStringValue(
            content=invalid_content, format="invalid"
        )
        paragraph = get_paragraphs(invalid_paragraph)
        self.assertEqual(paragraph[0], invalid_content)

    def test_fail_get_html_paragraph(self):
        """
        get_paragraphs_html should fail if called with the
        wrong paragraph format
        """
        paragraph = GenericStringValue(
            content="content", format="application/x-jats+xml"
        )
        with self.assertRaises(ValueError):
            get_paragraphs_html(paragraph)  # type: ignore

    def test_fail_get_jats_paragraph(self):
        """
        get_paragraphs_jats should fail if called with the
        wrong paragraph format
        """
        paragraph = GenericStringValue(content="content", format="text/html")
        with self.assertRaises(ValueError):
            get_paragraphs_jats(paragraph)  # type: ignore
