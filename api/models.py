from django.db import models


class RefData(models.Model):
    """
    .. important::

       This model is defined as non-managed by Django.
       There is no need to migrate this model.
       It is developer’s responsibility to keep field definition in sync
       with the model in bibxml-indexer.

       The model in bibxml-indexer is managed,
       and changes to that model require migrations to be applied.
    """

    ref = models.CharField(
        max_length=128,
        help_text="Reference (or ID). "
                  "Corresponds to source dataset filename without extension.")

    ref_id = models.CharField(max_length=64)
    """DEPRECATED: Use ref"""

    ref_type = models.CharField(max_length=24)
    """DEPRECATED: Use ref"""

    dataset = models.CharField(
        max_length=24,
        help_text="Internal dataset ID.")
    """Matches ID in settings.RELATON_DATASETS."""

    body = models.JSONField()
    """Contains canonical Relaton representation"""

    representations = models.JSONField()
    """Contains a mapping of { format: string }, where format is e.g. bibxml"""

    class Meta:
        db_table = 'api_ref_data'
        unique_together = [['ref', 'dataset']]
        managed = False
