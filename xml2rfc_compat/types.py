from typing import Optional
from pydantic.dataclasses import dataclass


@dataclass
class Xml2rfcPathMetadata:
    """Describes xml2rfc filename sidecar YAML data."""

    primary_docid: Optional[str] = None
    """Well-formed :term:`primary document identifier`
    that represents a bibliographic item corresponding
    to this filename.

    References :term:`docid.id` string value
    of the primary identifier of the target bibliographic item.
    """

    # primary_docid_type: Optional[str] = None
    # """Only has effect if primary_docid is supplied.
    #
    # Can be used if ``primary_docid`` field is ambiguous
    # and differentiation by docid type is necessary.
    # """

    invalid: Optional[bool] = False
    """Indicates that bibliographic item served by this
    xml2rfc path was created in error and not supposed to exist
    (does not map to a published resource, not represented
    by authoritative bibliographic data sources, and so on).
    """
