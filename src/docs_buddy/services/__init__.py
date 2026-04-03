"""Docs Buddy Service Layer"""

import functools
from typing import Protocol, Iterator, ContextManager, Callable
from pathlib import Path

from docs_buddy.common import PathLike, DocsBuddyError
from docs_buddy import domain


class RepositorySyncError(DocsBuddyError):
    pass


class RepoStorage(Protocol):
    """Protocol that manages repository updates"""

    def is_already_cloned(self) -> bool: ...

    def can_clone(self) -> bool: ...

    def pull_repo(self) -> None: ...

    def clone_repo(self, url: str) -> None: ...


class SupportsIntermediateStorage(Protocol):
    """Protocol providing for intermediate storage of results"""

    def get_temp_location(self) -> ContextManager[PathLike]: ...

    def replace_destination(self, temp_location: PathLike) -> None: ...


class DocsArtifactStorage(SupportsIntermediateStorage, Protocol):
    """Interface for extracting raw documents from storage repository"""

    def get_source_paths(self) -> Iterator[PathLike]: ...

    def read_from_source(self, path: PathLike) -> str: ...

    def write_to_location(
        self, content: str, path: PathLike, base_dir: PathLike
    ) -> None: ...


class DocumentIndex(Protocol):
    """Interface of an indexer providing fit and search capabilities"""

    def fit(
        self, chunks: Iterator[domain.DocumentChunk], destination: PathLike
    ) -> None: ...


class DocumentChunksPipeline(SupportsIntermediateStorage, Protocol):
    """Protocol for providing document chunks"""

    def get_document_chunks(self) -> Iterator[domain.DocumentChunk]: ...


def sync_repository(url: str, storage: RepoStorage) -> None:
    """Synchronizes a git repository to local storage"""

    if storage.is_already_cloned():
        storage.pull_repo()
    elif storage.can_clone():
        storage.clone_repo(url)
    else:
        raise RepositorySyncError("Unable to sync repository")


def update_document_artifacts(
    storage: DocsArtifactStorage, processor: Callable
) -> None:
    """Updates documentation artifacts using the provided processor

    Processes each file from source location into a temporary location.
    When processing is completed successfully, the destination is
    finally replaced with the newly processed artifacts
    """

    source_paths = storage.get_source_paths()

    with storage.get_temp_location() as tmp_location:
        for p in source_paths:
            content = storage.read_from_source(p)
            for artifact, dest_path in processor(content, p):
                storage.write_to_location(str(artifact), Path(dest_path), tmp_location)

        storage.replace_destination(tmp_location)


def process_raw_document(
    content: str, path: PathLike
) -> Iterator[tuple[domain.RawDocument, PathLike]]:
    """Return a representation of the raw document and destination path"""

    document_key = str(path)
    raw_doc = domain.RawDocument(content, document_key)
    path_no_extension, _ = document_key.rsplit(".", 1)
    dest_path = path_no_extension.replace("/", "_") + ".json"
    yield raw_doc, dest_path


def annotate_document(
    raw_content: str,
    path: PathLike,
    metadata_extractor: Callable[[str], tuple[dict, str]],
) -> Iterator[tuple[domain.AnnotatedDocument, PathLike]]:
    """Returns a document with metadata annotations and destination path"""
    raw_doc = domain.RawDocument.fromstring(raw_content)
    metadata, doc_content = metadata_extractor(raw_doc.content)
    yield domain.AnnotatedDocument(
        doc_content, path=raw_doc.path, metadata=metadata
    ), path


def chunk_document(
    raw_content: str,
    path: PathLike,
) -> Iterator[tuple[domain.DocumentChunk, PathLike]]:
    """Yields chunks of an annotated document"""
    annotated_doc = domain.AnnotatedDocument.fromstring(raw_content)
    for chunk_data in domain.overlapping_chunks(annotated_doc.content):
        dest_prefix, extension = str(path).rsplit(".", 1)

        chunk = domain.DocumentChunk(
            path=annotated_doc.path, metadata=annotated_doc.metadata, **chunk_data
        )

        dest_path = f"{dest_prefix}_{chunk.index}.{extension}"
        yield chunk, dest_path


def composed_processor(
    *processors: Callable[
        [str, PathLike], Iterator[tuple[domain.DocumentArtifact, PathLike]]
    ]
) -> Callable[[str, PathLike], Iterator[tuple[domain.DocumentArtifact, PathLike]]]:
    """Returns a processing pipeline using the processors"""

    def document_pipeline(content, path):
        """Processes a document artifact using the provided processors in order"""

        def apply(args, func):
            """Reducer that applies func to each (content, path) and flattens results."""
            yield from (
                result for content, path in args for result in func(str(content), path)
            )

        initial = iter([(content, path)])
        final_results = functools.reduce(apply, processors, initial)
        return final_results

    return document_pipeline


def index_document_chunks(
    pipeline: DocumentChunksPipeline, index: DocumentIndex
) -> None:
    document_chunks = pipeline.get_document_chunks()

    with pipeline.get_temp_location() as tmp_location:
        index.fit(document_chunks, destination=tmp_location)
        pipeline.replace_destination(tmp_location)
