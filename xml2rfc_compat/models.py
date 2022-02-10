import re
from django.db import models



dir_subpath_regex = (
    r'(?P<xml2rfc_subpath>%s/'
    r'_?reference\.(?P<anchor>[-A-Za-z0-9./_]+)\.xml'
    r')$'
)
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
