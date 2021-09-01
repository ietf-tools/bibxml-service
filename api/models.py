from django.db import models


class BibData(models.Model):
    bib_id = models.CharField(max_length=64)
    bib_type = models.CharField(max_length=16)
    body = models.JSONField('body')

    class Meta:
        db_table = 'api_bib_data'

        constraints = [
            models.UniqueConstraint(fields=['bib_id', 'bib_type'], name='unique_bib_id')
        ]