"""Docs Buddy Service Layer"""

from typing import Protocol, Iterator, ContextManager, Callable
from pathlib import Path

from docs_buddy.common import PathLike, DocsBuddyError
from docs_buddy.domain import RawDocument


class RepositorySyncError(DocsBuddyError):
    pass


class RepoStorage(Protocol):
    """Protocol that manages repository updates"""

    def is_already_cloned(self) -> bool: ...

    def can_clone(self) -> bool: ...

    def pull_repo(self) -> None: ...

    def clone_repo(self, url: str) -> None: ...


class DocsArtifactStorage(Protocol):
    """Interface for extracting raw documents from storage repository"""

    def get_source_paths(self) -> Iterator[PathLike]: ...

    def read_from_source(self, path: PathLike) -> str: ...

    def get_temp_location(self) -> ContextManager[PathLike]: ...

    def write_to_location(
        self, content: str, path: PathLike, base_dir: PathLike
    ) -> None: ...

    def replace_destination(self, temp_location: PathLike) -> None: ...


def sync_repository(url: str, storage: RepoStorage) -> None:
    """Synchronizes a git repository to local storage"""

    if storage.is_already_cloned():
        storage.pull_repo()
    elif storage.can_clone():
        storage.clone_repo(url)
    else:
        raise RepositorySyncError("Unable to refresh repository")


def update_document_artifacts(
    storage: DocsArtifactStorage, processor: Callable
) -> None:
    """Extracts documentation source files from local repository"""

    source_paths = storage.get_source_paths()

    with storage.get_temp_location() as tmp_location:
        for p in source_paths:
            content = storage.read_from_source(p)
            for artifact, dest_path in processor(content, p):
                storage.write_to_location(str(artifact), Path(dest_path), tmp_location)

        storage.replace_destination(tmp_location)


def process_raw_document(content, path):
    document_key = str(path)
    raw_doc = RawDocument(content, document_key)
    dest_path = document_key.replace("/", "_")
    yield raw_doc, dest_path
