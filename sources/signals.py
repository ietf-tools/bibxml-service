from datetime import datetime, timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver

from sources.models import SourceIndexationOutcome


@receiver(post_save, sender=SourceIndexationOutcome)
def delete_old_source_indexation_outcome_entries(sender, **kwargs):
    days = 9
    print(f"Deleting SourceIndexationOutcome entries older than {days} days.")
    SourceIndexationOutcome.objects.filter(timestamp__lte=datetime.now()-timedelta(days=days)).delete()
