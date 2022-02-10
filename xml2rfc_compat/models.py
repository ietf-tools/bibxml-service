import re
from django.db import models


dir_subpath_regex = (
    r'(?P<xml2rfc_subpath>%s/'
    r'_?reference\.(?P<anchor>[-A-Za-z0-9./_]+)\.xml'
    r')$'
)


def get_dir_subpath_regex(dirname: str):
    return re.compile(dir_subpath_regex % dirname)


class ManualPathMap(models.Model):
    """Maps an xml2rfc path to a search query.

    Search is defined by ``query`` and ``query_format``.
    Ideally, search query should unambiguously return one item,
    so ``json_struct`` matching with docid specified is best.

    We don’t map to DB-specific primary key values,
    because those may change.
    """

    xml2rfc_subpath = models.CharField(
        max_length=255,
        db_index=True,
        unique=True)
    """Corresponds to the :any:`Xml2rfcItem.subpath`."""

    docid = models.CharField(max_length=255, db_index=True)
    """Document ID (``docid.id``) to map this path to."""


class Xml2rfcItem(models.Model):
    """Represents an item at xml2rfc web server."""

    subpath = models.CharField(max_length=255, db_index=True)
    """File path relative to :data:`bibxml.settings.XML2RFC_PATH_PREFIX`."""

    xml_repr = models.TextField()
    """Contents of the file, XML as a string."""

    def format_filename(self):
        dirname = self.subpath.split('/')[0]
        return self.subpath.replace(f'{dirname}/', '', 1)

    def format_anchor(self):
        dirname = self.subpath.split('/')[0]
        match = re.match(get_dir_subpath_regex(dirname), self.subpath)
        if match:
            return match.group('anchor')
        else:
            return self.subpath
