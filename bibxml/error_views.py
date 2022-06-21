"""Error handlers for Django project’s root URL configuration."""

from typing import Union, Optional
from django.shortcuts import render


def server_error(request, *args, **kwargs):
    """Handler for HTTP 500 errors."""

    exc = kwargs.get('exception', None)
    return _render_error(request, "Server error (500)", exc)


def not_authorized(request, *args, **kwargs):
    """Handler for HTTP 403 errors."""

    exc = kwargs.get('exception', None)
    return _render_error(request, "Not authorized (403)", exc)


def not_found(request, *args, **kwargs):
    """Handler for HTTP 404 errors."""

    exc = kwargs.get('exception', None)

    exc_repr: Optional[str] = None

    if exc:
        resolver_404_path = _get_resolver_404_path(exc)
        if resolver_404_path:
            # Let’s sanitize Django’s resolver 404
            exc_repr = "Path “{}” could not be resolved".format(
                resolver_404_path)
        else:
            exc_repr = str(exc)

    return _render_error(request, "Not found (404)", exc_repr)


_get_resolver_404_path = (
  lambda exc:
  exc.args[0].get('path', None)
  if len(exc.args) > 0 and hasattr(exc.args[0], 'get')
  else None)
"""A helper that takes any exception
and if it looks like Django’s resolver 404 then returns a path,
otherwise ``None``."""


def _render_error(
    request,
    title: str,
    exc: Union[Exception, None, str],
):
    """Generic error view.

    Renders the ``error.html`` template with given title and error description.

    If error description is an instance of :class:`Exception`,
    casts it to string."""

    exc_repr = (
        exc
        if exc is None or isinstance(exc, str)
        else str(exc))
    return render(
        request,
        'error.html',
        dict(
          error_description=exc_repr,
          error_title=title))
