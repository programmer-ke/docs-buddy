"""Composition root for dependency injection"""

import functools
from pathlib import Path

from docs_buddy import services, adapters
from docs_buddy.services import commands, events, handlers
from docs_buddy.common import PathLike

frontmatter_annotate_document = functools.partial(
    services.annotate_document,
    metadata_extractor=adapters.frontmatter_metadata_extractor,
)


def get_message_bus(
    repository_storage_path: PathLike,
    chunks_storage_path: PathLike,
    lexical_index_storage_path: PathLike,
    doc_extensions: tuple[str, ...],
) -> handlers.MessageBus:
    """Create and configure the application message bus with all dependencies.

    Args:
        repository_storage_path: Path to the cloned repository storage.
        chunks_storage_path: Path where processed document chunks are stored.
        lexical_index_storage_path: Path where the Whoosh lexical index is stored.

    Returns:
        A configured InMemoryMessageBus with registered command and event handlers.
    """

    # todo: better message-handler mapping and dependency bootstrapping
    message_bus = adapters.InMemoryMessageBus()
    repo_storage = adapters.FileSystemRepoStorage(repository_storage_path)
    docs_storage = adapters.FileSystemDocsStorage(
        repository_storage_path, chunks_storage_path, doc_extensions
    )
    chunks_pipeline = adapters.FileSystemDocumentChunksPipeline(
        chunks_storage_path, lexical_index_storage_path
    )
    whoosh_document_index = adapters.WhooshIndexBuilder()

    sync_repository_handler = functools.partial(
        handlers.sync_repository,
        repo_storage=repo_storage,
        message_bus=message_bus,
    )

    document_processor = services.composed_processor(
        services.process_raw_document,
        frontmatter_annotate_document,
        services.chunk_document,
    )

    update_document_artifacts_handler = functools.partial(
        handlers.update_document_artifacts,
        storage=docs_storage,
        processor=document_processor,
        message_bus=message_bus,
    )

    index_document_chunks_handler = functools.partial(
        handlers.index_document_chunks,
        chunks_pipeline=chunks_pipeline,
        index=whoosh_document_index,
        message_bus=message_bus,
    )

    message_bus.register_command_handler(commands.SyncRepo, sync_repository_handler)
    message_bus.register_command_handler(
        commands.UpdateDocumentArtifacts, update_document_artifacts_handler
    )
    message_bus.register_command_handler(
        commands.UpdateDocumentIndex, index_document_chunks_handler
    )

    notify_repository_synced_handler = functools.partial(
        handlers.notify_repository_synced,
        notifier=adapters.log_repository_synced,
    )

    notify_document_artifacts_updated_handler = functools.partial(
        handlers.notify_document_artifacts_update,
        notifier=adapters.log_document_artifacts_updated,
    )

    notify_index_updated_handler = functools.partial(
        handlers.notify_index_updated,
        notifier=adapters.log_index_updated,
    )

    message_bus.register_event_handler(
        events.RepositorySynced, notify_repository_synced_handler
    )
    message_bus.register_event_handler(
        events.DocumentArtifactsUpdated, notify_document_artifacts_updated_handler
    )
    message_bus.register_event_handler(
        events.DocumentIndexUpdated, notify_index_updated_handler
    )

    return message_bus
