"""Service commands"""

from docs_buddy._vendor import miniattrs


class Command:
    """Commands that trigger domain changes"""


@miniattrs.define
class SyncRepo(Command):
    """Trigger syncing of repository indicated by url"""

    url: str
    branch: str


class UpdateDocumentArtifacts(Command):
    """Trigger updating the document artifacts"""


class UpdateDocumentIndex(Command):
    """Trigger updating the document index"""
