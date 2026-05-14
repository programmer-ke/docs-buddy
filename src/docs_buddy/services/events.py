"""Service events"""

from dataclasses import dataclass


class Event:
    """Events that is generated from domain changes"""


@dataclass(frozen=True)
class RepositorySynced(Event):
    """Indicate that repository has been synced"""

    url: str


@dataclass(frozen=True)
class DocumentArtifactsUpdated(Event):
    """Indicate that document artifacts have been updated"""


@dataclass(frozen=True)
class DocumentIndexUpdated(Event):
    """Indicate that the index has been updated"""
