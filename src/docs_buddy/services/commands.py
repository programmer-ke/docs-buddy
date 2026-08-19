"""Service commands"""

from dataclasses import dataclass


class Command:
    """Commands that trigger domain changes"""


@dataclass(frozen=True)
class SyncRepo(Command):
    """Trigger syncing of repository indicated by url"""

    url: str
    branch: str


@dataclass(frozen=True)
class UpdateDocumentArtifacts(Command):
    """Trigger updating the document artifacts"""


@dataclass(frozen=True)
class UpdateDocumentIndex(Command):
    """Trigger updating the document index"""
