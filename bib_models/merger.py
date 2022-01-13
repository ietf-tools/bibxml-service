"""
Helpers for merging dictionary representations
of BibliographicItem models.
"""

from typing import Any
from deepmerge import Merger, STRATEGY_END
from common.util import as_list


def deduplicate_and_coerce_to_list(
        config, path,
        base: Any, nxt: Any):
    """
    Takes two values, any or both of which could be lists,
    and merges as a combined list unless values are identical.

    ``None`` values are omitted.

    Doesn’t flatten recursively.

    For example:

    - If neither ``base`` nor ``nxt`` is a list, produces ``[base, nxt]``.
    - If ``base`` == ``nxt``, produces ``base``.
    - If only ``base`` is a list, produces effectively ``[*base, nxt]``.

    Suitable as list, fallback and type-conflict deepmerge strategy.
    """

    if base == nxt or None in [base, nxt]:
        return base or nxt

    else:
        list1, list2 = as_list(base), as_list(nxt)
        for item in list2:
            if item not in list1:
                list1.append(item)
        return [item for item in list1 if item is not None]

    return STRATEGY_END


bibitem_merger = Merger(
    [
        (list, [deduplicate_and_coerce_to_list]),
        (dict, ['merge']),
        (set, ['union']),
    ],
    [deduplicate_and_coerce_to_list],
    [deduplicate_and_coerce_to_list],
)
