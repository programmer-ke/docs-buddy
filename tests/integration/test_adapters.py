"""Adapter tests that interact with infrastructure"""

import pytest
from pathlib import Path
import shutil
import tempfile
import json

import whoosh.index

from docs_buddy import adapters, domain


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


def test_whoosh_document_index_fit_creates_index() -> None:
    """Test that WhooshDocumentIndex creates an index from DocumentChunks."""

    with tempfile.TemporaryDirectory() as temp_dir:

        indexer = adapters.WhooshDocumentIndex()

        chunks = [
            domain.DocumentChunk.fromstring(json.dumps(_SAMPLE_CHUNK_1)),
            domain.DocumentChunk.fromstring(json.dumps(_SAMPLE_CHUNK_2)),
        ]

        # Call fit method
        indexer.fit(iter(chunks), temp_dir)

        # Verify index files were created
        index_files = list(Path(temp_dir).glob("*"))
        assert len(index_files) > 0

        # Verify we can open the index
        ix = whoosh.index.open_dir(temp_dir)

        # Verify index contains documents
        with ix.searcher() as searcher:
            assert searcher.doc_count() == 2

            # Verify we can retrieve the documents
            all_docs = list(searcher.documents())
            assert len(all_docs) == 2

            # Verify content was stored
            for doc in all_docs:
                assert "content" in doc
                assert "path" in doc
                assert doc["path"] == "DOCUMENTATION_AI_GUIDE.md"
                assert "metadata" in doc


def test_whoosh_document_index_fitting_for_empty_documents() -> None:
    """Test that WhooshDocumentIndex creates an index from DocumentChunks."""

    with tempfile.TemporaryDirectory() as temp_dir:

        indexer = adapters.WhooshDocumentIndex()

        sample_chunk = {
            "chunk": "",
            "index": 0,
            "path": "DOCUMENTATION_AI_GUIDE.md",
            "metadata": {},
        }

        chunks = [
            domain.DocumentChunk.fromstring(json.dumps(sample_chunk)),
        ]

        # Call fit method
        indexer.fit(iter(chunks), temp_dir)

        # Verify index files were created
        index_files = list(Path(temp_dir).glob("*"))
        assert len(index_files) > 0

        # Verify we can open the index
        ix = whoosh.index.open_dir(temp_dir)

        # Verify index contains documents
        with ix.searcher() as searcher:
            assert searcher.doc_count() == 1


def test_filesystem_document_chunks_pipeline_yields_chunks() -> None:
    """Test that FileSystemDocumentChunksPipeline reads JSON files and yields DocumentChunks."""

    # Create a temporary source directory
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir)
        dest_dir = Path(tempfile.mkdtemp())

        # Create JSON files with the sample chunk data
        chunk1_path = source_dir / "chunk1.json"
        chunk2_path = source_dir / "chunk2.json"

        chunk1_path.write_text(json.dumps(_SAMPLE_CHUNK_1))
        chunk2_path.write_text(json.dumps(_SAMPLE_CHUNK_2))

        # Create the pipeline
        pipeline = adapters.FileSystemDocumentChunksPipeline(
            source=source_dir, destination=dest_dir, doc_extensions=("json",)
        )

        # Get chunks and convert to list for verification
        chunks = list(pipeline.get_document_chunks())

        # Verify we got 2 chunks
        assert len(chunks) == 2

        # Verify the chunks contain the expected data
        retrieved_chunks = [json.loads(str(c)) for c in chunks]

        assert _SAMPLE_CHUNK_1 in retrieved_chunks
        assert _SAMPLE_CHUNK_2 in retrieved_chunks

        # Clean up destination
        shutil.rmtree(dest_dir)


_SAMPLE_CHUNK_1 = {
    "chunk": '```markdown\n## What is a Deployment?\n\nA deployment is your application running on the Akash Network. When you \ncreate a deployment, you\'re requesting compute resources (CPU, RAM, storage) \nfrom providers on the network.\n\nThink of it like renting a server, but:\n- Pay only for what you use (per-block pricing)\n- Choose from multiple providers bidding on your request\n- Your app runs in an isolated container\n```\n\n### For Developers (Technical Users)\n\n**Audience:** Developers integrating Akash\n\n**Requirements:**\n- Assume CLI/programming familiarity\n- Focus on concepts and integration patterns\n- Provide multi-language examples (curl, Go, TypeScript)\n- Link to detailed API reference\n- Show best practices and common patterns\n- Include error handling\n\n**Tone:** Professional, technical, concise\n\n**Example:**\n```markdown\n## Query Providers via gRPC\n\nThe provider query service returns all registered providers and their attributes.\n\n\\```go\nclient, _ := provider.NewQueryClient(conn)\nres, _ := client.Providers(context.Background(), &provider.QueryProvidersRequest{})\n\\```\n\nFilter by attribute:\n\\```go\nreq := &provider.QueryProvidersRequest{\n    Filters: &provider.ProviderFilters{\n        Attributes: []*v1beta3.Attribute{\n            {Key: "region", Value: "us-west"},\n        },\n    },\n}\n\\```\n```\n\n### For Providers (System Administrators)\n\n**Audience:** DevOps engineers, system administrators\n\n**Requirements:**\n- Assume Linux/Kubernetes knowledge\n- Be precise with commands and versions\n- Include all prerequisites\n- Provide verification steps\n- Add comprehensive troubleshooting\n- Emphasize security best practices\n- Provide automated solutions first, manual as fallback\n\n**Tone:** Direct, technical, security-conscious\n\n**Example:**\n```markdown\n## STEP 3: Configure Persistent Storage\n\nInstall Rook-Ceph for persistent storage classes (beta1, beta2, beta3).\n\n**Prerequisites:**\n- Dedicated drives (not partitions) on each worker node\n- Minimum 4 SSDs or 2 NVMe SSDs across cluster\n- Drives mus',
    "index": 13000,
    "path": "DOCUMENTATION_AI_GUIDE.md",
    "metadata": {
        "title": "AI Guide",
        "pubDate": "2023-01-15T19:23:18+02:00",
        "draft": False,
    },
}

_SAMPLE_CHUNK_2 = {
    "chunk": 'Providers(context.Background(), &provider.QueryProvidersRequest{})\n\\```\n\nFilter by attribute:\n\\```go\nreq := &provider.QueryProvidersRequest{\n    Filters: &provider.ProviderFilters{\n        Attributes: []*v1beta3.Attribute{\n            {Key: "region", Value: "us-west"},\n        },\n    },\n}\n\\```\n```\n\n### For Providers (System Administrators)\n\n**Audience:** DevOps engineers, system administrators\n\n**Requirements:**\n- Assume Linux/Kubernetes knowledge\n- Be precise with commands and versions\n- Include all prerequisites\n- Provide verification steps\n- Add comprehensive troubleshooting\n- Emphasize security best practices\n- Provide automated solutions first, manual as fallback\n\n**Tone:** Direct, technical, security-conscious\n\n**Example:**\n```markdown\n## STEP 3: Configure Persistent Storage\n\nInstall Rook-Ceph for persistent storage classes (beta1, beta2, beta3).\n\n**Prerequisites:**\n- Dedicated drives (not partitions) on each worker node\n- Minimum 4 SSDs or 2 NVMe SSDs across cluster\n- Drives must be unformatted\n\n\\```bash\n# Verify available drives (should show no filesystem)\nlsblk -f\n\n# Expected: Empty FSTYPE column for target drives\n\\```\n\n**Important:** Do not use system drives or shared partitions. Rook-Ceph \nrequires exclusive access to raw block devices.\n```\n\n### For Node Operators (Blockchain Engineers)\n\n**Audience:** Blockchain node operators, validators\n\n**Requirements:**\n- Assume blockchain experience\n- Focus on node operations and security\n- Document upgrade procedures clearly\n- Include monitoring and alerting\n- Separate architecture (for devs) from operations (for ops)\n- Provide recovery procedures\n\n**Tone:** Technical, security-focused, precise\n\n**Example:**\n```markdown\n## Validator Security with TMKMS\n\nTMKMS (Tendermint Key Management System) separates your validator key \nfrom the node, adding a critical security layer.\n\n**Architecture:**\n- Validator node runs on Akash (no private key)\n- TMKMS runs on local machine (holds private key)\n- Stunnel provides encrypted c',
    "index": 14000,
    "path": "DOCUMENTATION_AI_GUIDE.md",
    "metadata": {},
}
