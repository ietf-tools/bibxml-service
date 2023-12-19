from typing import cast, List, Optional

from lxml import objectify
from lxml.etree import _Element
from relaton.models import Organization, PersonAffiliation, ContactMethod, Address, GenericStringValue, Contributor

__all__ = (
    'create_author',
    'is_author',
    'AUTHOR_ROLES',
)

from common.util import as_list

E = objectify.E


AUTHOR_ROLES = set(('author', 'editor', 'publisher'))
"""Relaton contributor role types that represent xml2rfc authors."""


is_author = (
    lambda contrib:
    len(set([r.type for r in as_list(contrib.role or [])]) & AUTHOR_ROLES) > 0
)
"""Returns ``True`` if given Relaton contributor instance
represents an author in xml2rfc domain."""


def is_rfc_publisher(contrib):
    """Returns ``True`` if contributor belongs
    to ``RFC Publisher`` organization"""
    if org := contrib.organization:
        if any(name.content == "RFC Publisher" for name in as_list(org.name)):
            return True
    return False


def filter_contributors(contribs):
    """Filter contributors by checking that they
    are authors and that they do not belong to
    ``RFC Publisher`` organization.
    """
    return [
        contrib
        for contrib in contribs
        if is_author(contrib) and not is_rfc_publisher(contrib)
    ]


def create_author(contributor: Contributor) -> _Element:
    if not is_author(contributor):
        raise ValueError(
            "Unable to construct <author>: incompatible roles")

    if not contributor.organization and not contributor.person:
        raise ValueError(
            "Unable to construct <author>: "
            "neither an organization nor a person")

    author_el = E.author()

    roles: List[str] = [
        r.type
        for r in (contributor.role or [])
        if r.type
    ]
    if 'editor' in roles:
        author_el.set('role', 'editor')

    org: Optional[Organization] = None
    if contributor.organization:
        org = contributor.organization
    elif contributor.person:
        affiliations: List[PersonAffiliation] = \
            as_list(contributor.person.affiliation or [])
        if len(affiliations) > 0:
            org = affiliations[0].organization
        else:
            org = None

    if org is not None:
        # Organization
        if (
            org.abbreviation is not None
            and org.abbreviation.content == 'IANA'
        ) or (
            org.name
            and any(
                name
                for name in as_list(org.name)
                if name.content == 'Internet Assigned Numbers Authority')
        ):
            org_el = E.organization('IANA')
        else:
            org_el = E.organization(as_list(org.name)[0].content)

            if org.abbreviation is not None:
                org_el.set('abbrev', org.abbreviation.content)

        author_el.append(org_el)

        # Address & postal
        contacts: List[ContactMethod] = as_list(org.contact or [])
        postal_contacts: List[Address] = [
            c.address for c in contacts
            if c.address and c.address.country
        ]
        if len(postal_contacts) > 0 or org.url:
            addr = E.address()

            if len(postal_contacts) > 0:
                contact = postal_contacts[0]
                postal = E.postal(
                    E.country(contact.country)
                )
                if contact.city:
                    postal.append(E.city(contact.city))
                addr.append(postal)

            if org.url:
                addr.append(E.uri(org.url))

            author_el.append(addr)

    if contributor.person:
        name = contributor.person.name

        # Simplify initials
        # from a list of formatted strings to a list of plain strings
        initials: List[str] = []
        if name.given:
            initials = [
                # We don’t expect trailing full stops in initials
                # Workaround for bad source data, in effect
                i.content.strip()
                for i in cast(
                    List[GenericStringValue],
                    as_list(name.given.formatted_initials or []),
                )
            ]

        if name.completename:
            author_el.set('fullname', name.completename.content)
        else:
            # Craft a complete name based on what we have
            # It’s clunky and error-prone,
            # but the alternative is only having a surname
            # in absence of ``completename``,
            # and ``completename`` is optional in Relaton.
            if name.given:
                forenames = ' '.join(
                    f.content
                    for f in as_list(name.given.forename or [])
                    if f.content is not None
                )
            else:
                forenames = None
            author_el.set('fullname', ('%s%s%s%s%s' % (
                f"{name.prefix.content} " if name.prefix else '',
                f"{forenames} " if forenames else '',
                ' '.join(initials) if len(initials) > 0 else '',
                f"{name.surname.content} " if name.surname else '',
                f"{name.addition.content} " if name.addition else '',
            )).strip())

        # Even if completename is given, these can still be provided:

        if name.surname:
            author_el.set('surname', name.surname.content)

        if len(initials) > 0:
            author_el.set('initials', ' '.join(initials))

    return author_el
