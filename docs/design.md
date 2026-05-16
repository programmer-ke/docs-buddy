# Project Design

## Repository Structure

### Main package

The package is rooted at `src/docs_buddy`.

The structure underneath the package is as follows:

#### domain

Domain entities and domain services

#### service

Use case handlers, adapter interfaces, events and commands

#### adapter

Infrastructure level implementations

#### entrypoint

This is the presentation layer exposed to the external world.

### Tests

Tests are structured as follows:

#### unit

Tests for domain & service functionality and other isolated components

#### integration

Tests that span multiple layers of the architecture

#### e2e

End-to-end tests of functionality exposed at the entrypoints

## Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI (__main__.py)
    participant Bus as Message Bus
    participant Handler as Handler (handlers.py)
    participant UseCase as Use Case (use_cases.py)
    participant Storage as Repository Storage
    participant Logger as Logging Adapter

    User->>CLI: Run with --repo-id --update-sources
    CLI->>Bus: send(SyncRepo(url))
    activate Bus
    Bus->>Handler: execute sync_repository handler
    activate Handler
    Handler->>UseCase: sync_repository(url, storage)
    activate UseCase
    UseCase->>Storage: pull_repo() or clone_repo(url)
    UseCase-->>Handler: (completes)
    deactivate UseCase
    Handler->>Bus: publish(RepositorySynced(url))
    Handler->>Bus: send(UpdateDocumentArtifacts)
    deactivate Handler
    deactivate Bus

    Bus->>Handler: execute update_document_artifacts handler
    activate Handler
    Handler->>UseCase: update_document_artifacts(storage, processor)
    Handler->>Bus: publish(DocumentArtifactsUpdated)
    Handler->>Bus: send(UpdateDocumentIndex)
    deactivate Handler

    Bus->>Handler: execute index_document_chunks handler
    activate Handler
    Handler->>UseCase: index_document_chunks(pipeline, index)
    Handler->>Bus: publish(DocumentIndexUpdated)
    deactivate Handler

    Bus->>Logger: notify_index_updated()
    Logger-->>CLI: log update message
    CLI-->>User: Sync complete
```
