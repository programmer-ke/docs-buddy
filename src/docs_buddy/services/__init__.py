"""Docs Buddy Service Layer"""

from typing import Protocol, Iterator, ContextManager
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

    def get_source_paths(self) -> Iterator[PathLike]: ...

    def read_from_source(self, path: PathLike) -> str: ...

    def get_temp_location(self) -> ContextManager[PathLike]: ...

    def write_to_location(self, content: str, path: PathLike, base_dir: PathLike): ...

    def replace_destination(self, temp_location: PathLike): ...


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

    source_paths = storage.get_source_paths()

    with storage.get_temp_location() as tmp_location:
        for p in source_paths:
            content = storage.read_from_source(p)
            document_key = str(p)
            raw_doc = RawDocument(content, document_key)
            dest_path = document_key.replace("/", "_")
            storage.write_to_location(str(raw_doc), Path(dest_path), tmp_location)

        storage.replace_destination(tmp_location)
