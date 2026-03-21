import ast
import json
import pytest
from pathlib import Path

from docs_buddy import domain
from docs_buddy.services import (
    sync_repository,
    update_document_artifacts,
    process_raw_document,
    annotate_document,
    RepositorySyncError,
)
from docs_buddy.adapters import FakeRepoStorage, FakeDocsStorage


def test_syncing_existing_repository() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = FakeRepoStorage(location)
    storage.fake_is_cloned = True
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"
    sync_repository(github_url, storage)
    assert len(storage.actions) == 1
    [(action,)] = storage.actions
    assert action == "PULL"


def test_syncing_non_existent_repo_and_can_clone() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = FakeRepoStorage(location)
    storage.fake_is_cloned = False
    storage.fake_can_clone = True
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"
    sync_repository(github_url, storage)
    assert len(storage.actions) == 1
    [(action, url, target)] = storage.actions
    assert action == "CLONE"
    assert url == github_url
    assert target == location


def test_syncing_non_existent_repo_and_cannot_clone() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = FakeRepoStorage(location)
    storage.fake_is_cloned = False
    storage.fake_can_clone = False
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"

    with pytest.raises(RepositorySyncError):
        sync_repository(github_url, storage)

    assert len(storage.actions) == 0


def test_document_artifact_update_existing_content_replaced() -> None:
    destination = ".docs/programmer-ke/akash-docs-buddy"
    source = ".repo/programmer-ke/akash-docs-buddy"
    storage = FakeDocsStorage(source, destination)

    existing_content = {
        "old_path_1.json": json.dumps(
            {"content": "old_foo", "path": "old_path_1.json"}
        ),
        "old_path_2.json": json.dumps(
            {"content": "old_foo", "path": "old_path_2.json"}
        ),
    }

    storage.sink[destination] = existing_content

    update_document_artifacts(storage, process_raw_document)

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
    storage = FakeDocsStorage(source, destination)

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
        update_document_artifacts(storage, process_raw_document)

    # existing content preserved
    assert storage.sink[destination] == existing_content

    # temporary destination should have been cleared
    expected_tmp_dir = destination + ".tmp"
    assert expected_tmp_dir not in storage.sink


def test_raw_document_processing() -> None:

    source_key = "path/to/file.mdx"
    content = "some file content"

    [(raw_doc, dest_key)] = list(process_raw_document(content, source_key))

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
        annotate_document(raw_document, source_path, metadata_extractor=fake_extractor)
    )

    assert str(dest_key) == str(source_path)
    assert annotated_doc.content == content
    assert annotated_doc.path == source_key
    assert annotated_doc.metadata == metadata
