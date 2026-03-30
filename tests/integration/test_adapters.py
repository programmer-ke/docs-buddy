"""Adapter tests that interact with infrastructure"""

import pytest
from pathlib import Path
import shutil
import tempfile

from docs_buddy import adapters


def test_get_temp_location_creates_and_cleans_up() -> None:

    storage = adapters.FileSystemIntermediateStorage("somedest")

    with storage.get_temp_location() as temp_dir:
        temp_path = Path(temp_dir)
        assert temp_path.exists()
        assert temp_path.is_dir()
        # Write a file to ensure it's writable
        test_file = temp_path / "test.txt"
        test_file.write_text("hello")
        assert test_file.exists()

    # After context exit, the temporary directory should be gone
    assert not temp_path.exists()


def test_replace_destination_moves_temp_to_destination() -> None:

    dest_dir = Path(tempfile.mkdtemp())
    storage = adapters.FileSystemIntermediateStorage(dest_dir)

    with storage.get_temp_location() as temp_dir:
        temp_path = Path(temp_dir)
        # Populate temp directory
        (temp_path / "file1.txt").write_text("content1")
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "file2.txt").write_text("content2")
        # Perform the replacement
        storage.replace_destination(temp_path)

    # Destination should now contain the files
    assert dest_dir.exists()
    assert (dest_dir / "file1.txt").read_text() == "content1"
    assert (dest_dir / "subdir" / "file2.txt").read_text() == "content2"

    # The temporary directory should no longer exist (moved)
    assert not temp_path.exists()

    shutil.rmtree(dest_dir)
    assert not dest_dir.exists()


def test_replace_destination_overwrites_existing_destination() -> None:

    dest_dir = Path(tempfile.mkdtemp())
    storage = adapters.FileSystemIntermediateStorage(dest_dir)

    # Create an existing destination with some content
    (dest_dir / "old.txt").write_text("old content")

    with storage.get_temp_location() as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "new.txt").write_text("new content")
        storage.replace_destination(temp_path)

    # Destination should now contain only the new content
    assert dest_dir.exists()
    assert (dest_dir / "new.txt").read_text() == "new content"
    assert not (dest_dir / "old.txt").exists()

    shutil.rmtree(dest_dir)
    assert not dest_dir.exists()
