"""Datatracker API integration.

.. seealso:: :rfp:req:`15`
"""


from . import request
from .exceptions import UnexpectedDatatrackerResponse

from . import internet_drafts
# Make external source register.


__all__ = (
    'request',
    'UnexpectedDatatrackerResponse',
)
