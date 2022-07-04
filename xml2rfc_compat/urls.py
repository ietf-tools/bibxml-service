"""
Provides utilities for constructing patterns
fit for inclusion in site’s root URL configuration.
"""
from django.urls import re_path
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .aliases import get_aliases
from .models import dir_subpath_regex
from .adapters import adapters
from .views import handle_xml2rfc_path


def get_urls():
    """Returns a list of URL patterns suitable for inclusion
    in site’s root URL configuration, based on registered adapters.

    The directory name for each registered adapter is automatically
    expanded to include aliases
    (e.g., “bibxml-ids” is included in addition to canonical “bibxml3”).

    Adapters should have been all registered prior
    to calling this function.

    Each generated URL pattern is in the shape of
    ``<dirname>/[_]reference.<xml2rfc anchor>.xml``,
    and constructed view handles bibliographic item resolution
    according to :ref:`xml2rfc-path-resolution-algorithm`.

    .. seealso:: :func:`.handle_xml2rfc_path` for how requests are handled.
    """
    dirnames_with_aliases = [
        d
        for dirname in adapters.keys()
        for d in [dirname, *get_aliases(dirname)]
    ]
    return [
        re_path(
            dir_subpath_regex % dirname,
            never_cache(require_safe(handle_xml2rfc_path)),
            name='xml2rfc_%s' % dirname)
        for dirname in dirnames_with_aliases
    ]
