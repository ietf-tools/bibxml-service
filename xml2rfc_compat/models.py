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
