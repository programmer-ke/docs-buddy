"""Docs Buddy Service Layer"""

from typing import Protocol, Iterator
from pathlib import Path

from docs_buddy.common import PathLike, DocsBuddyError
from docs_buddy.domain import RawDocument


class RepositorySyncError(DocsBuddyError):
    pass


class RepoStorage(Protocol):
    """Manages repository updates"""

    def is_already_cloned(self) -> bool: ...

    def can_clone(self) -> bool: ...

    def pull_repo(self): ...

    def clone_repo(self, url: str): ...


class DocsStorage(Protocol):
    """Interface for extracting raw documents from storage repository"""

    def destination_exists(self) -> bool: ...

    def create_destination(self): ...

    def destination_empty(self) -> bool: ...

    def clear_destination(self): ...

    def get_source_paths(self) -> Iterator[PathLike]: ...

    def read_from_source(self, path: PathLike) -> str: ...

    def write_to_dest(self, content: str, path: PathLike): ...


def sync_repository(url: str, storage: RepoStorage):
    """Synchronizes a git repository to local storage"""

    if storage.is_already_cloned():
        storage.pull_repo()
    elif storage.can_clone():
        storage.clone_repo(url)
    else:
        raise RepositorySyncError("Unable to refresh repository")


def extract_documentation(storage: DocsStorage):
    """Extracts documentation source files from local repository"""

    if not storage.destination_exists():
        storage.create_destination()

    if not storage.destination_empty():
        storage.clear_destination()

    source_paths = storage.get_source_paths()

    for p in source_paths:
        content = storage.read_from_source(p)
        document_key = str(p)
        raw_doc = RawDocument(content, document_key)
        dest_path = document_key.replace("/", "_")
        storage.write_to_dest(str(raw_doc), Path(dest_path))
