"""Service events"""

from docs_buddy._vendor import miniattrs


class Event:
    """Event that is generated from domain changes"""


@miniattrs.define
class RepositorySynced(Event):
    """Indicate that repository has been synced"""

    url: str
    branch: str


class DocumentArtifactsUpdated(Event):
    """Indicate that document artifacts have been updated"""


class DocumentIndexUpdated(Event):
    """Indicate that the index has been updated"""
