from django.db import models


class SourceIndexationOutcome(models.Model):
    source_id = models.CharField(max_length=250, db_index=True)
    """Identifier of the :term:`indexable source`."""

    task_id = models.CharField(max_length=250, db_index=True, unique=True)
    """Celery task ID."""

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    """When this run concluded."""

    successful = models.BooleanField(default=False)
    """Whether this run was successful."""

    notes = models.TextField(default='')
    """Any notes, e.g. warnings or stats."""
