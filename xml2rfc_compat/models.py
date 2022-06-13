import re
from django.db import models


dir_subpath_regex = (
    r'(?P<xml2rfc_subpath>'
    r'(?P<dirname>%s)/'
    r'_?reference\.(?P<anchor>[-A-Za-z0-9./_]+)\.xml'
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

    def format_filename(self):
        """Extracts filename from this item’s ``subpath``."""

        dirname = self.subpath.split('/')[0]
        return self.subpath.replace(f'{dirname}/', '', 1)

    def format_anchor(self):
        """Extracts :term:`xml2rfc anchor` from this item’s ``subpath``."""

        dirname = self.subpath.split('/')[0]
        match = re.match(get_dir_subpath_regex(dirname), self.subpath)
        if match:
            return match.group('anchor')
        else:
            return self.subpath


class ManualPathMap(models.Model):
    """Manually maps an xml2rfc path to a bibliographic item,
    overriding any automatic resolution.

    .. seealso:: :func:`xml2rfc_compat.views.resolve_manual_map()`
    """

    xml2rfc_subpath = models.CharField(
        max_length=255,
        db_index=True,
        unique=True)
    """Corresponds to the :any:`Xml2rfcItem.subpath` being mapped."""

    docid = models.CharField(max_length=255, db_index=True)
    """:term:`docid.id` of the bibliographic item that should be returned."""
