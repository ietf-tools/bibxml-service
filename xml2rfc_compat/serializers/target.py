from typing import List


from relaton.models import Link


__all__ = (
  'get_suitable_target',
)


def get_suitable_target(links: List[Link]):
    """From a list of :class:`~relaton.models.links.Link` instances,
    return a string suitable to be used as value of ``target`` attribute
    on root XML element.

    It prefers a link with ``type`` set to “src”,
    if not present then first available link.
    """
    try:
        target: Link = (
            [l for l in links if l.type in ('src', 'pdf')]
            or links)[0]
    except IndexError:
        raise ValueError("Unable to find a suitable target (no links given)")
    else:
        return target.content
