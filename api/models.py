from django.db import models


class BibData(models.Model):
    bib_id = models.CharField(max_length=64)
    bib_type = models.CharField(max_length=16)
    body = models.JSONField("body")

    class Meta:
        managed = False
        db_table = 'bib_data'
        unique_together = [['bib_id', 'bib_type']]