import ast
import json
import re
import functools
import pytest
from pathlib import Path

from docs_buddy import domain, services, adapters


def test_syncing_existing_repository() -> None:
    # Given an already-cloned repository
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = adapters.FakeRepoStorage(location)
    storage.fake_is_cloned = True
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"

    # When we synchronise
    services.sync_repository(github_url, storage)

    # Then a pull is performed
    assert len(storage.actions) == 1
    [(action,)] = storage.actions
    assert action == "PULL"


def test_syncing_non_existent_repo_and_can_clone() -> None:
    # Given a non‑existent repository that can be cloned
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = adapters.FakeRepoStorage(location)
    storage.fake_is_cloned = False
    storage.fake_can_clone = True
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"

    # When we synchronise
    services.sync_repository(github_url, storage)

    # Then a clone is performed with the correct URL and target
    assert len(storage.actions) == 1
    [(action, url, target)] = storage.actions
    assert action == "CLONE"
    assert url == github_url
    assert target == location


def test_syncing_non_existent_repo_and_cannot_clone() -> None:
    # Given a non‑existent repository that cannot be cloned
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = adapters.FakeRepoStorage(location)
    storage.fake_is_cloned = False
    storage.fake_can_clone = False
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"

    # When we try to synchronise
    # Then a RepositorySyncError is raised
    with pytest.raises(services.RepositorySyncError):
        services.sync_repository(github_url, storage)

    # And no storage action was recorded
    assert len(storage.actions) == 0


def test_document_artifact_update_existing_content_replaced() -> None:
    # Given existing processed artifacts in the destination
    destination = ".docs/programmer-ke/akash-docs-buddy"
    source = ".repo/programmer-ke/akash-docs-buddy"
    storage = adapters.FakeDocsStorage(source, destination)

    existing_content = {
        "old_path_1.json": json.dumps(
            {"content": "old_foo", "path": "old_path_1.json"}
        ),
        "old_path_2.json": json.dumps(
            {"content": "old_foo", "path": "old_path_2.json"}
        ),
    }
    storage.sink[destination] = existing_content

    # When we update the document artifacts
    services.update_document_artifacts(storage, services.process_raw_document)

    # Then a fresh temporary location is created
    assert len(storage.actions) == 3
    [(action0, target0), (action1, target1), (action2, src, target2)] = storage.actions

    expected_tmp_dir = destination + ".tmp"

    assert action0 == "MKDIR"
    assert target0 == expected_tmp_dir

    # Then the old destination is removed
    assert action1 == "RMRF"
    assert target1 == destination

    # Then the temporary location replaces the destination
    assert action2 == "MV"
    assert src == expected_tmp_dir
    assert target2 == destination

    # And the new content differs from the old content
    assert storage.sink[destination] != existing_content


def test_artifact_updates_existing_content_preserved_on_error() -> None:
    # Given existing processed artifacts and a pipeline that will fail
    destination = ".docs/programmer-ke/akash-docs-buddy"
    source = ".repo/programmer-ke/akash-docs-buddy"
    storage = adapters.FakeDocsStorage(source, destination)

    existing_content = {
        "old_path_1.json": json.dumps(
            {"content": "old_foo", "path": "old_path_1.json"}
        ),
        "old_path_2.json": json.dumps(
            {"content": "old_foo", "path": "old_path_2.json"}
        ),
    }
    storage.sink[destination] = existing_content

    # Corrupt the sources so processing raises an exception
    for k in storage.sources:
        storage.sources[k] = object()  # type: ignore

    # When updating document artifacts
    with pytest.raises(TypeError):
        services.update_document_artifacts(storage, services.process_raw_document)

    # Then the existing content remains untouched
    assert storage.sink[destination] == existing_content

    # And the temporary directory was cleaned up
    expected_tmp_dir = destination + ".tmp"
    assert expected_tmp_dir not in storage.sink


def test_raw_document_processing() -> None:
    # Given a source document
    source_key = "path/to/file.mdx"
    content = "some file content"

    # When we process it as a raw document
    [(raw_doc, dest_key)] = list(services.process_raw_document(content, source_key))

    # Then the destination path is transformed correctly
    assert str(dest_key) == source_key.replace("/", "_").replace("mdx", "json")

    # And the document content and original path are preserved
    assert raw_doc.content == content
    assert raw_doc.path == source_key


def test_metadata_extraction() -> None:
    # Given a document with metadata embedded as a prefix
    source_key = "path/to/file.md"
    source_path = "path_to_file.json"
    content = "some content"
    metadata = {"title": "foo", "author": "bar"}
    source_text = f"{metadata}|{content}"
    raw_document = domain.RawDocument(source_text, source_key)

    def fake_extractor(content):
        metadata, text = content.split("|")
        return ast.literal_eval(metadata), text

    # When we annotate the document
    [(annotated_doc, dest_key)] = list(
        services.annotate_document(
            str(raw_document), source_path, metadata_extractor=fake_extractor
        )
    )

    # Then the destination path is unchanged
    assert str(dest_key) == str(source_path)

    # Then the metadata is extracted correctly
    assert annotated_doc.metadata == metadata

    # Then the content and original path are preserved
    assert annotated_doc.content == content
    assert annotated_doc.path == source_key


def test_document_chunking() -> None:
    """Test that documents are properly chunked with metadata preserved."""

    # Given an annotated document
    source_path = "docs/intro.json"
    metadata = {"title": "Introduction", "author": "Alice"}
    content = "This is a sample document. " * 100

    annotated_doc = domain.AnnotatedDocument(
        content=content, path=source_path, metadata=metadata
    )
    raw_content = str(annotated_doc)

    # When we chunk the document
    results = list(services.chunk_document(raw_content, source_path))

    # Then multiple chunks are produced
    assert len(results) > 1

    for chunk, dest_path in results:
        # And each chunk is a DocumentChunk with preserved metadata and path
        assert isinstance(chunk, domain.DocumentChunk)
        assert chunk.metadata == metadata
        assert chunk.path == source_path

        # And the destination path includes the chunk index
        prefix, extension = source_path.rsplit(".", 1)
        assert str(dest_path).startswith(prefix)
        assert re.match(f"{prefix}_{chunk.index}\\.json", str(dest_path))


def test_composed_pipeline() -> None:
    # Given a document with metadata and content
    source_key = "path/to/file.mdx"
    content = "some file content" * 1000
    metadata = {"title": "foo", "author": "bar"}
    source_text = f"{metadata}|{content}"

    def fake_extractor(content):
        metadata, text = content.split("|")
        return ast.literal_eval(metadata), text

    annotate_document = functools.partial(
        services.annotate_document, metadata_extractor=fake_extractor
    )
    process_document = services.composed_processor(
        services.process_raw_document, annotate_document, services.chunk_document
    )

    # When we run the composed pipeline
    chunk_data = list(process_document(source_text, source_key))

    # Then we get at least one chunk
    assert len(chunk_data) > 0

    for chunk, path in chunk_data:
        # And each chunk is a DocumentChunk with required fields
        assert isinstance(chunk, domain.DocumentChunk)
        assert isinstance(chunk.index, int)
        assert chunk.metadata == metadata
        assert str(path).endswith(".json")

    # And all output paths are unique
    paths = {path for _, path in chunk_data}
    assert len(paths) == len(chunk_data)


def test_can_index_documents() -> None:
    # Given a fake chunks pipeline and an in‑memory index
    source = ".chunks/programmmer-ke/akash-docs-buddy"
    dest = ".index/programmer-ke/akash-docs-buddy"
    pipeline = adapters.FakeDocumentChunksPipeline(source, dest)
    index = adapters.FakeIndex(pipeline)

    assert dest not in pipeline.sink

    # When we index the document chunks
    services.index_document_chunks(pipeline, index)

    # Then the index destination contains DocumentChunk items
    assert len(pipeline.sink[dest]) > 0
    for item in pipeline.sink[dest]:
        assert isinstance(item, domain.DocumentChunk)

    # And the intermediate storage performed the expected operations
    [(action1, arg1), (action2, arg2), (action3, arg3_1, arg3_2)] = pipeline.actions

    tmp_location = f"{dest}.tmp"
    assert (action1, arg1) == ("MKDIR", tmp_location)
    assert (action2, arg2) == ("RMRF", dest)
    assert (action3, arg3_1, arg3_2) == ("MV", tmp_location, dest)


def test_find_answer_with_configured_agent() -> None:
    # Given the documentation index has been built
    source = ".chunks/test-repo"
    dest = ".index/test-repo"
    pipeline = adapters.FakeDocumentChunksPipeline(source, dest)
    index = adapters.FakeIndex(pipeline)
    services.index_document_chunks(pipeline, index)

    # And an agent has been configured with a search tool
    tools = [adapters.make_search_tool(index)]
    research_user_query = adapters.make_fake_research_agent(prompt="some prompt")

    # When user submits valid query
    query = domain.Query("provider")
    response = services.find_answer(query, research_user_query, tools)

    # Then the system returns a structured response
    assert isinstance(response, domain.QueryResponse)

    # Then the answer is non‑empty
    assert response.answer

    # Then there is at least one citation
    assert len(response.citations) > 0


def test_agent_error_gracefully_handled() -> None:
    # Given the documentation index has been built
    source = ".chunks/test-repo"
    dest = ".index/test-repo"
    pipeline = adapters.FakeDocumentChunksPipeline(source, dest)
    index = adapters.FakeIndex(pipeline)
    services.index_document_chunks(pipeline, index)

    # And an agent has been configured with a search tool
    tools = [adapters.make_search_tool(index)]
    research_user_query = adapters.make_fake_research_agent(prompt="some prompt")

    # When user submits query likely to fail
    query = domain.Query("nonexistent")
    response = services.find_answer(query, research_user_query, tools)

    # Then the system returns a structured response
    assert isinstance(response, domain.QueryResponse)

    # Then the answer is non‑empty
    assert "went wrong" in response.answer

    # Then citation list is empty
    assert len(response.citations) == 0
