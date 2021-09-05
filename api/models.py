from django.db import models


class RefData(models.Model):
    ref_id = models.CharField(max_length=64)
    ref_type = models.CharField(max_length=24)
    dataset = models.CharField(max_length=24)
    body = models.JSONField('body')

    class Meta:
        db_table = 'api_ref_data'

        constraints = [
            models.UniqueConstraint(fields=['ref_id', 'dataset'], name='unique_dataset_id')
        ]