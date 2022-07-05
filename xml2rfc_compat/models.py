from typing import Optional
import re
from django.db import models
from django.db.models.query import QuerySet


dir_subpath_regex = (
    r'(?P<xml2rfc_subpath>'
    r'(?P<dirname>%s)/'
    r'_?reference\.(?P<anchor>[-+;()A-Za-z0-9./_]+)\.xml'
    r')$'
)
"""Django’s URL path regular expression
for an :term:`xml2rfc-style path`,
excluding :data:`bibxml.settings.XML2RFC_PATH_PREFIX`.

Provides the following components to view functions:

- ``xml2rfc_subpath``: the whole subpath after the prefix.
- ``dirname``: dirname only, e.g. bibxml3 or bibxml-ids.
- ``anchor``: the part after ``reference.`` prefix
  and before file extension.
"""


def get_dir_subpath_regex(dirname: str):
    """Returns a compiled :data:`.dir_subpath_regex`,
    substituting ``xml2rfc_subpath`` with given ``dirname``."""
    return re.compile(dir_subpath_regex % dirname)


class Xml2rfcItem(models.Model):
    """Represents an item at an :term:`xml2rfc-style path`."""

    subpath = models.CharField(max_length=255, db_index=True)
    """File path, relative to :data:`bibxml.settings.XML2RFC_PATH_PREFIX`
    with no leading slash."""

    xml_repr = models.TextField()
    """Contents of the file (XML as a string)."""

    sidecar_meta = models.JSONField()
    """Contains optional metadata that, for example, maps this filename
    of :term:`bibliographic item`.

    The shape of it is supposed
    to conform to :class:`xml2rfc_compat.types.Xml2rfcPathMetadata`.

    Can be used to construct
    a :class:`relaton.models.bibdata.BibliographicItem` instance.
    """

    def format_dirname(self):
        """Extracts xml2rfc dirname from this item’s ``subpath``."""

        return self.subpath.split('/', 1)[0]

    def format_filename(self):
        """Extracts filename from this item’s ``subpath``."""

        dirname = self.format_dirname()
        return self.subpath.replace(f'{dirname}/', '', 1)

    def format_anchor(self):
        """Extracts :term:`xml2rfc anchor` from this item’s ``subpath``."""

        dirname = self.format_dirname()
        match = re.match(get_dir_subpath_regex(dirname), self.subpath)
        if match:
            return match.group('anchor')
        else:
            return self.subpath


def get_xml2rfc_items_for_dir(dirname: str) -> QuerySet[Xml2rfcItem]:
    """Returns a QuerySet of Xml2rfcItem objects
    given canonical (unaliased) ``dirname`` (e.g., “bibxml2”).
    """
    _dirname = dirname.removesuffix('/')
    return Xml2rfcItem.objects.filter(subpath__startswith=f'{_dirname}/')


def get_mapped_xml2rfc_items(
    dirname: Optional[str] = None,
) -> QuerySet[Xml2rfcItem]:
    """Returns a QuerySet of Xml2rfcItem objects
    that have non-empty ``primary_id`` in their ``sidecar_meta``.

    Optionally, only returns items under the canonical (unaliased) ``dirname``
    (e.g., “bibxml2”).
    """
    if dirname:
        _dirname = dirname.removesuffix('/')
        kwargs = dict(
            subpath__startswith=f'{_dirname}/',
        )
    else:
        kwargs = dict()
    return Xml2rfcItem.objects.filter(
        **kwargs,
        sidecar_meta__primary_docid__isnull=False,
    )
