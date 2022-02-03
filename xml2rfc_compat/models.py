from django.db import models


class Xml2rfcItem(models.Model):
    """Represents an item at xml2rfc web server."""

    subpath = models.CharField(max_length=255, db_index=True)
    """File path relative to /public/rfc."""

    xml_repr = models.TextField()
    """Contents of the file, XML as a string."""
