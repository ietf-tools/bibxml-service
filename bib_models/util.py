from typing import cast, Optional, List, Tuple, Dict, Any
import logging

from pydantic import ValidationError

from common.pydantic import ValidationErrorDict

from relaton.models.bibdata import BibliographicItem


log = logging.getLogger(__name__)


def construct_bibitem(data: Dict[str, Any], strict=True) -> Tuple[
    BibliographicItem,
    Optional[List[ValidationErrorDict]],
]:
    """
    Constructs a :class:`relaton.models.bibdata.BibliographicItem`
    instance, given source data as a dict.

    Optionally, suppresses validation errors and returns them separately
    to be shown to the user.

    :param dict data:
        Bibliographic item data as a dict, e.g. deserialized from YAML.
    :param bool strict:
        See :ref:`strict-validation`.
    :returns:
        a 2-tuple ``(bibliographic item, validation errors)``,
        where errors may be None or a list of Pydantic’s ErrorDicts.
    """
    errors: Optional[List[ValidationErrorDict]] = None

    if strict:
        bibitem = BibliographicItem(**data)
    else:
        try:
            bibitem = BibliographicItem(**data)
        except ValidationError as e:
            log.warn(
                "Unexpected bibliographic item format: %s, %s",
                data.get('docid', 'docid N/A'),
                e)
            errors = cast(List[ValidationErrorDict], e.errors())
            bibitem = BibliographicItem.construct(**data)

    return bibitem, errors
