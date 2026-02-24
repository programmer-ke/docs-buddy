import docs_buddy
import json
import pytest
from pathlib import Path


def test_raw_document_serialization() -> None:
    d = docs_buddy.RawDocument(content="foo", path="bar")
    assert str(d) == json.dumps({"content": "foo", "path": "bar"})


def test_syncing_existing_repository() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = docs_buddy.FakeRepoStorage(location)
    storage.fake_is_cloned = True
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"
    docs_buddy.sync_repository(github_url, storage)
    assert len(storage.actions) == 1
    [(action,)] = storage.actions
    assert action == "PULL"


def test_syncing_non_existent_repo_and_can_clone() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = docs_buddy.FakeRepoStorage(location)
    storage.fake_is_cloned = False
    storage.fake_can_clone = True
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"
    docs_buddy.sync_repository(github_url, storage)
    assert len(storage.actions) == 1
    [(action, url, target)] = storage.actions
    assert action == "CLONE"
    assert url == github_url
    assert target == location


def test_syncing_non_existent_repo_and_cannot_clone() -> None:
    location = ".repo/programmer-ke/akash-docs-buddy"
    storage = docs_buddy.FakeRepoStorage(location)
    storage.fake_is_cloned = False
    storage.fake_can_clone = False
    github_url = "https://github.com/programmer-ke/akash-docs-buddy.git"

    with pytest.raises(docs_buddy.RepositoryRefreshError):
        docs_buddy.sync_repository(github_url, storage)

    assert len(storage.actions) == 0


def test_document_extraction_directory_creation() -> None:
    destination = ".docs/programmer-ke/akash-docs-buddy"
    source = ".repo/programmer-ke/akash-docs-buddy"
    storage = docs_buddy.FakeDocsStorage(source, destination)
    storage.fake_destination_exists = False
    storage.fake_destination_empty = True
    docs_buddy.extract_documentation(storage)
    [(action, target)] = storage.actions
    assert action == "MKDIR"
    assert target == destination


def test_document_extraction_existing_content_cleared() -> None:
    destination = ".docs/programmer-ke/akash-docs-buddy"
    source = ".repo/programmer-ke/akash-docs-buddy"
    storage = docs_buddy.FakeDocsStorage(source, destination)
    storage.fake_destination_exists = True
    storage.fake_destination_empty = False
    docs_buddy.extract_documentation(storage)
    [(action, target)] = storage.actions
    assert action == "RMRF"
    assert target == destination


def test_document_extraction_existing_files_processed() -> None:
    destination = ".docs/programmer-ke/akash-docs-buddy"
    source = ".repo/programmer-ke/akash-docs-buddy"
    storage = docs_buddy.FakeDocsStorage(source, destination)
    storage.fake_destination_exists = True
    storage.fake_destination_empty = True
    docs_buddy.extract_documentation(storage)

    expected_read_paths = storage.sources.keys()
    assert expected_read_paths == storage.read_paths

    expected_written_paths = [k.replace("/", "_") for k in storage.sources.keys()]
    for p in expected_written_paths:
        assert p in storage.sink
