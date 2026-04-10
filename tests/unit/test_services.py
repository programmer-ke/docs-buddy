import ast
import json
import re
import functools
import pytest
from pathlib import Path

from docs_buddy import domain, services, adapters


def test_syncing_existing_repository() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = adapters.FakeRepoStorage(location)
    storage.fake_is_cloned = True
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"
    services.sync_repository(github_url, storage)
    assert len(storage.actions) == 1
    [(action,)] = storage.actions
    assert action == "PULL"


def test_syncing_non_existent_repo_and_can_clone() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = adapters.FakeRepoStorage(location)
    storage.fake_is_cloned = False
    storage.fake_can_clone = True
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"
    services.sync_repository(github_url, storage)
    assert len(storage.actions) == 1
    [(action, url, target)] = storage.actions
    assert action == "CLONE"
    assert url == github_url
    assert target == location


def test_syncing_non_existent_repo_and_cannot_clone() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = adapters.FakeRepoStorage(location)
    storage.fake_is_cloned = False
    storage.fake_can_clone = False
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"

    with pytest.raises(services.RepositorySyncError):
        services.sync_repository(github_url, storage)

    assert len(storage.actions) == 0


def test_document_artifact_update_existing_content_replaced() -> None:
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

    services.update_document_artifacts(storage, services.process_raw_document)

    assert len(storage.actions) == 3
    [(action0, target0), (action1, target1), (action2, src, target2)] = storage.actions

    expected_tmp_dir = destination + ".tmp"

    assert action0 == "MKDIR"
    assert target0 == expected_tmp_dir

    assert action1 == "RMRF"
    assert target1 == destination

    assert action2 == "MV"
    assert src == expected_tmp_dir
    assert target2 == destination

    assert storage.sink[destination] != existing_content


def test_artifact_updates_existing_content_preserved_on_error() -> None:
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

    # create non json-serializable sources to trigger exception
    for k in storage.sources:
        storage.sources[k] = object()  # type: ignore

    with pytest.raises(TypeError):
        services.update_document_artifacts(storage, services.process_raw_document)

    # existing content preserved
    assert storage.sink[destination] == existing_content

    # temporary destination should have been cleared
    expected_tmp_dir = destination + ".tmp"
    assert expected_tmp_dir not in storage.sink


def test_raw_document_processing() -> None:

    source_key = "path/to/file.mdx"
    content = "some file content"

    [(raw_doc, dest_key)] = list(services.process_raw_document(content, source_key))

    assert str(dest_key) == source_key.replace("/", "_").replace("mdx", "json")
    assert raw_doc.content == content
    assert raw_doc.path == source_key


def test_metadata_extraction() -> None:

    source_key = "path/to/file.md"
    source_path = "path_to_file.json"
    content = "some content"
    metadata = {"title": "foo", "author": "bar"}
    source_text = f"{metadata}|{content}"
    raw_document = domain.RawDocument(source_text, source_key)

    def fake_extractor(content):
        metadata, text = content.split("|")
        return ast.literal_eval(metadata), text

    [(annotated_doc, dest_key)] = list(
        services.annotate_document(
            str(raw_document), source_path, metadata_extractor=fake_extractor
        )
    )

    assert str(dest_key) == str(source_path)
    assert annotated_doc.content == content
    assert annotated_doc.path == source_key
    assert annotated_doc.metadata == metadata


def test_document_chunking() -> None:
    """Test that documents are properly chunked with metadata preserved."""

    # Create an annotated document as a string
    source_path = "docs/intro.json"
    metadata = {"title": "Introduction", "author": "Alice"}
    content = "This is a sample document. " * 100  # Make it long enough to chunk

    # Create an AnnotatedDocument and convert to string
    annotated_doc = domain.AnnotatedDocument(
        content=content, path=source_path, metadata=metadata
    )
    raw_content = str(annotated_doc)

    # Test chunking
    results = list(services.chunk_document(raw_content, source_path))

    # Verify we got chunks
    assert len(results) > 1

    for chunk, dest_path in results:
        assert isinstance(chunk, domain.DocumentChunk)
        assert chunk.metadata == metadata
        assert chunk.path == source_path

        # check that chuck index is appended to path
        prefix, extension = source_path.rsplit(".", 1)
        assert str(dest_path).startswith(prefix)
        assert re.match(f"{prefix}_{chunk.index}\\.json", str(dest_path))


def test_composed_pipeline() -> None:

    # raw document
    source_key = "path/to/file.mdx"
    content = "some file content" * 1000
    metadata = {"title": "foo", "author": "bar"}
    source_text = f"{metadata}|{content}"

    # processors
    def fake_extractor(content):
        metadata, text = content.split("|")
        return ast.literal_eval(metadata), text

    annotate_document = functools.partial(
        services.annotate_document, metadata_extractor=fake_extractor
    )

    process_document = services.composed_processor(
        services.process_raw_document, annotate_document, services.chunk_document
    )

    chunk_data = list(process_document(source_text, source_key))
    assert len(chunk_data) > 0

    for chunk, path in chunk_data:
        assert isinstance(chunk, domain.DocumentChunk)
        assert isinstance(chunk.index, int)
        assert chunk.metadata == metadata
        assert str(path).endswith(".json")

    # confirm that the paths are unique
    paths = {path for _, path in chunk_data}
    assert len(paths) == len(chunk_data)


def test_can_index_documents() -> None:
    source = ".chunks/programmmer-ke/akash-docs-buddy"
    dest = ".index/programmer-ke/akash-docs-buddy"

    pipeline = adapters.FakeDocumentChunksPipeline(source, dest)
    index = adapters.FakeIndex(pipeline)

    assert dest not in pipeline.sink

    services.index_document_chunks(pipeline, index)

    assert len(pipeline.sink[dest]) > 0

    for item in pipeline.sink[dest]:
        assert isinstance(item, domain.DocumentChunk)

    [(action1, arg1), (action2, arg2), (action3, arg3_1, arg3_2)] = pipeline.actions

    # assert correct order of operations
    tmp_location = f"{dest}.tmp"
    assert (action1, arg1) == ("MKDIR", tmp_location)
    assert (action2, arg2) == ("RMRF", dest)
    assert (action3, arg3_1, arg3_2) == ("MV", tmp_location, dest)
