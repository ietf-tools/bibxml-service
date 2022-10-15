from django.db import models
from django.db.models.functions import Cast
from django.db.models.fields.json import KeyTransform
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector


class RefData(models.Model):
    """Holds bibliographic item data sourced from a dataset,
    for use by internal sources.

    Always contains a Relaton representation,
    and can contain pre-crafted representations in other formats
    (like ``bibxml``).

    Model meta notes:

    - Explicit table name ``api_ref_data`` is used
    - ``ref`` and ``dataset`` combinations must be unique
    """

    dataset = models.CharField(
        max_length=24,
        help_text="Internal dataset ID.",
        db_index=True)
    """
    Which dataset given citation was indexed from.
    Matches indexable source ID in :any:`RELATON_DATASETS`.
    """

    ref = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Reference (or ID). "
                  "Corresponds to source dataset filename without extension.")
    """
    Corresponds to object name within source dataset,
    filename extension excluded. See :term:`ref`.
    """

    body = models.JSONField()
    """Canonical Relaton representation
    of :term:`bibliographic item`.
    Can be used to construct
    a :class:`relaton.models.bibdata.BibliographicItem` instance.
    """

    latest_date = models.DateField()
    """Latest publication or revision date found on the item.
    Used e.g. when ordering results.
    Do not use when displaying data, since this field does not preserve
    specificity (use bibliographic item’s
    :attr:`~relaton.models.bibdata.BibliographicItem.date` attribute
    instead).
    """

    representations = models.JSONField(default=dict)
    """Contains alternative representations of the citation.
    A mapping of ``{ <format_id>: <freeform string> }``,
    where format is e.g. “bibxml”.

    .. deprecated:: 2022.2

       XML is obtained on the fly
       using :mod:`xml2rfc_compat.serializer`.

       The property is no longer filled in, but is left in place
       in case a choice is made to pre-serialize representations
       at indexing stage.
    """

    ref_id = models.CharField(max_length=64)
    # DEPRECATED: Use ref

    ref_type = models.CharField(max_length=24)
    # DEPRECATED: Use ref

    class Meta:
        db_table = 'api_ref_data'
        unique_together = [['ref', 'dataset']]
        indexes = [
            # TODO: Identify & remove unused indices
            GinIndex(
                fields=['body'],
                name='body_gin',
            ),
            GinIndex(
                SearchVector(
                    Cast('body', models.TextField()),
                    config='english'),
                name='body_astext_gin',
            ),
            GinIndex(
                SearchVector(
                    KeyTransform('docid', 'body'),
                    config='english'),
                name='body_docid_gin',
            ),
            GinIndex(
                SearchVector(
                    'body',
                    config='english'),
                name='body_ts_gin',
            ),
            # TODO: Add more specific indexes for RefData.body subfields
        ]
