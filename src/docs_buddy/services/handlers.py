"""Service handlers"""

from typing import Protocol, Callable
from docs_buddy.services import commands, events, use_cases


class MessageBus(Protocol):
    """The message bus protocol"""

    def send(self, command: commands.Command) -> None: ...

    def publish(self, event: events.Event) -> None: ...


def sync_repository(
    repo_storage: use_cases.RepoStorage,
    message_bus: MessageBus,
    command: commands.SyncRepo,
) -> None:
    """Trigger repository sync"""

    use_cases.sync_repository(command.url, command.branch, repo_storage)

    message_bus.publish(events.RepositorySynced(url=command.url, branch=command.branch))
    message_bus.send(commands.UpdateDocumentArtifacts())


def notify_repository_synced(
    event: events.RepositorySynced, notifier: Callable
) -> None:
    """Notify that repository has been synced"""

    notifier(event.url)


def notify_document_artifacts_update(
    event: events.DocumentArtifactsUpdated, notifier: Callable
) -> None:
    """Notify that document artifacts have been updated"""

    notifier()


def notify_index_updated(
    event: events.DocumentIndexUpdated, notifier: Callable
) -> None:
    """Notify that index has been updated"""

    notifier()


def update_document_artifacts(
    storage: use_cases.DocsArtifactStorage,
    processor: Callable,
    message_bus: MessageBus,
    command: commands.UpdateDocumentArtifacts,
) -> None:

    use_cases.update_document_artifacts(storage, processor)
    message_bus.publish(events.DocumentArtifactsUpdated())
    message_bus.send(commands.UpdateDocumentIndex())


def index_document_chunks(
    chunks_pipeline: use_cases.DocumentChunksPipeline,
    index: use_cases.DocumentIndexBuilder,
    message_bus: MessageBus,
    command: commands.UpdateDocumentIndex,
) -> None:

    use_cases.index_document_chunks(chunks_pipeline, index)
    message_bus.publish(events.DocumentIndexUpdated())
