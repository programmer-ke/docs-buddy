"""Docs buddy adapters reside here"""

from contextlib import contextmanager
from typing import Iterator, Any
from pathlib import Path
import subprocess
import shutil
import tempfile
import json

import frontmatter

from docs_buddy.common import PathLike
from docs_buddy import domain


class FakeRepoStorage:
    """In-memory test implementation of RepoStorage protocol."""

    def __init__(self, target: PathLike):
        self._target = target
        self.fake_is_cloned: bool
        self.fake_can_clone: bool
        self.actions: list = []

    def __repr__(self):
        classname = type(self).__name__
        return f"{classname}({self._target!r})"

    def is_already_cloned(self) -> bool:
        return self.fake_is_cloned

    def can_clone(self) -> bool:
        return self.fake_can_clone

    def clone_repo(self, url: str) -> None:
        self.actions.append(("CLONE", url, self._target))

    def pull_repo(self):
        self.actions.append(("PULL",))


class FileSystemRepoStorage:
    """File system implementation of RepoStorage protocol."""

    def __init__(self, target):
        self._target = target

    def __repr__(self):
        classname = type(self).__name__
        return f"{classname}({self._target!r})"

    def is_already_cloned(self) -> bool:
        return self._is_git_repository(self._target)

    def pull_repo(self):
        self._update_repository(self._target)

    def clone_repo(self, url: str) -> None:
        self._clone_repository(url, self._target)

    def can_clone(self):
        """Indicates whether we can clone a new repo in the target

        Valid conditions:
        - The target location doesn't exist (git will create it)
        - The target location is an empty directory
        """
        path = Path(self._target)
        return not path.exists() or self._is_empty_dir(path)

    @staticmethod
    def _is_empty_dir(path: Path) -> bool:
        """Check if a directory exists and is empty."""
        return path.is_dir() and not any(path.iterdir())

    @staticmethod
    def _is_git_repository(directory: str) -> bool:
        """Check if a directory contains a .git subdirectory."""
        git_dir = Path(directory) / ".git"
        return git_dir.exists() and git_dir.is_dir()

    @staticmethod
    def _clone_repository(url: str, target_dir: str) -> None:
        """Clone a git repository with depth 1."""
        subprocess.run(
            ["git", "clone", "--depth", "1", url, target_dir],
            check=True,
            capture_output=True,
        )

    @staticmethod
    def _update_repository(directory: str) -> None:
        """Pull latest changes from a git repository."""
        subprocess.run(["git", "pull"], cwd=directory, check=True, capture_output=True)


class FakeIntermediateStorage:
    """In memory implementation of intermediate storage provider"""

    def __init__(self, destination):
        self._destination = Path(destination)
        self.sink = {}

    def __repr__(self):
        classname = type(self).__name__
        return f"{classname}({self._destination!r})"

    @contextmanager
    def get_temp_location(self):
        temp_location = str(self._destination) + ".tmp"
        self.sink[temp_location] = {}
        try:
            yield temp_location
        finally:
            self.sink.pop(temp_location, None)

    def replace_destination(self, temp_location: PathLike) -> None:
        self.sink[str(self._destination)] = self.sink.pop(temp_location)


class FakeDocsStorage:
    """In-memory test implementation of DocsArtifactStorage protocol."""

    def __init__(self, source: PathLike, destination: PathLike):
        self._source = Path(source)
        self._destination = Path(destination)
        self._intermediate_storage = FakeIntermediateStorage(destination)
        self.actions: list = []
        self.read_paths: set = set()

        self.sources = {
            "src/content/Docs/index.md": _SAMPLE_DOC_2,
            "src/content/Development_Page/welcome/index.mdx": _SAMPLE_DOC_1,
        }

    def __repr__(self):
        classname = type(self).__name__
        return f"{classname}({self._source!r}, {self._destination!r})"

    @property
    def sink(self):
        return self._intermediate_storage.sink

    @contextmanager
    def get_temp_location(self):
        with self._intermediate_storage.get_temp_location() as temp_location:
            self.actions.append(("MKDIR", temp_location))
            yield temp_location

    def get_source_paths(self) -> Iterator[PathLike]:
        for k in self.sources.keys():
            yield Path(k)

    def read_from_source(self, nested_path: PathLike) -> str:
        key = str(nested_path)
        self.read_paths.add(key)
        return self.sources[key]

    def write_to_location(
        self, content: str, path: PathLike, base_dir: PathLike
    ) -> None:
        self._intermediate_storage.sink[str(base_dir)][str(path)] = content

    def replace_destination(self, temp_location: PathLike) -> None:
        self._intermediate_storage.replace_destination(temp_location)
        self.actions.append(("RMRF", str(self._destination)))
        self.actions.append(("MV", str(temp_location), str(self._destination)))


class FakeDocumentChunksPipeline:
    """Fake implementation of the document chunk pipeline"""

    def __init__(self, source: PathLike, destination: PathLike):
        self._source = source
        self._destination = destination
        self._intermediate_storage = FakeIntermediateStorage(destination)

        self._chunks = [_SAMPLE_CHUNK_1, _SAMPLE_CHUNK_2]
        self.actions: list = []

    @property
    def sink(self):
        return self._intermediate_storage.sink

    @contextmanager
    def get_temp_location(self):
        with self._intermediate_storage.get_temp_location() as temp_location:
            self.actions.append(("MKDIR", temp_location))
            yield temp_location

    def replace_destination(self, temp_location: PathLike) -> None:
        self._intermediate_storage.replace_destination(temp_location)
        self.actions.append(("RMRF", str(self._destination)))
        self.actions.append(("MV", str(temp_location), str(self._destination)))

    def get_document_chunks(self):
        return (
            domain.DocumentChunk.fromstring(json.dumps(chunk)) for chunk in self._chunks
        )


class FakeIndex:
    """Implements a document index for in memory testing"""

    def __init__(self, pipeline):
        self._pipeline = pipeline

    def fit(self, chunks, destination):
        """Index document chunks in memory"""
        self._pipeline.sink[destination] = list(chunks)


class FileSystemIntermediateStorage:
    """File system implementation of the intermediate storage protocol"""

    def __init__(self, destination: PathLike):
        self._destination = Path(destination)

    def __repr__(self):
        classname = type(self).__name__
        return f"{classname}({self._destination!r})"

    @contextmanager
    def get_temp_location(self, prefix=""):
        """
        Create a temporary directory for atomic writes.

        Yields:
            Path to temporary directory
        """
        with tempfile.TemporaryDirectory(
            prefix=(prefix or f"{self._destination.name}_")
        ) as temp_dir:
            yield Path(temp_dir)

    def replace_destination(self, temp_location: PathLike) -> None:
        """Replaces the destination with the provided temp_location"""

        temp_path = Path(temp_location)
        dest_path = self._destination

        if dest_path.exists():
            shutil.rmtree(dest_path)

        shutil.move(str(temp_path), str(dest_path))


class FileSystemDocumentChunksPipeline:
    """Implements the filesytem document chunks pipeline protocol"""

    def __init__(
        self,
        source: PathLike,
        destination: PathLike,
        doc_extensions: tuple[str, ...] = ("json",),
    ):
        self._source = Path(source)
        self._dest = Path(destination)
        self._intermediate_storage = FileSystemIntermediateStorage(destination)
        self._doc_extensions = doc_extensions

    def get_document_chunks(self) -> Iterator[domain.DocumentChunk]:
        """Yields chunked documents from the source"""
        doc_paths = (
            p
            for ext in self._doc_extensions
            for p in Path(self._source).rglob(f"*.{ext}")
        )

        for path in doc_paths:
            content = _read_file(path)
            chunk = domain.DocumentChunk.fromstring(content)
            yield chunk

    def get_temp_location(self):
        """Yields a temp location by delegating to intermediate storage"""
        with self._intermediate_storage.get_temp_location() as temp_location:
            yield temp_location

    def replace_destination(self, temp_location: PathLike) -> None:
        """Replace destination with temp location by delegating to intermediate storage"""
        self._intermediate_storage.replace_destination(temp_location)


class FileSystemDocsStorage:
    """File system implementation of DocsArtifactStorage protocol."""

    def __init__(
        self,
        source: PathLike,
        destination: PathLike,
        doc_extensions: tuple[str, ...] = ("mdx", "md"),
    ):
        """
        Initialize storage with source and destination paths.

        Args:
            source: Directory containing source documents
            destination: Directory where processed documents will be written
            doc_extensions: File extensions to consider as documents
        """
        self._destination = Path(destination)
        self._source = Path(source)
        self._doc_extensions = doc_extensions
        self._intermediate_storage = FileSystemIntermediateStorage(destination)

    def __repr__(self):
        classname = type(self).__name__
        return f"{classname}({self._source!r}, {self._destination!r})"

    @contextmanager
    def get_temp_location(self, prefix=""):
        """
        Create a temporary directory for atomic writes.

        Yields:
            Path to temporary directory
        """
        with self._intermediate_storage.get_temp_location() as temp_dir:
            yield Path(temp_dir)

    def get_source_paths(self) -> Iterator[PathLike]:
        """
        Get all document paths from the source directory.

        Yields:
            Relative paths to documents within source directory
        """
        documentation_paths = (
            p
            for ext in self._doc_extensions
            for p in Path(self._source).rglob(f"*.{ext}")
        )
        for full_path in documentation_paths:
            nested_path = full_path.relative_to(self._source)
            yield nested_path

    def read_from_source(self, nested_path: PathLike) -> str:
        """
        Read content from a source document.

        Args:
            nested_path: Relative path within source directory

        Returns:
            Document content as string
        """
        full_path = Path(self._source) / nested_path
        return _read_file(full_path)

    def write_to_location(
        self, content: str, path: PathLike, base_dir: PathLike
    ) -> None:
        """
        Write content to a location within a base directory.

        Args:
            content: Document content to write
            path: Relative path within base directory
            base_dir: Base directory for writing
        """
        full_path = Path(base_dir) / path
        self._write_file(full_path, content)

    def replace_destination(self, temp_location: PathLike) -> None:
        """Replaces the destination with the provided temp_location"""

        self._intermediate_storage.replace_destination(temp_location)

    @staticmethod
    def _is_empty_dir(path: Path) -> bool:
        """Check if a directory exists and is empty."""
        return path.is_dir() and not any(path.iterdir())

    @staticmethod
    def _write_file(path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write content to file with specified encoding."""
        with open(path, "wt", encoding=encoding) as f:
            f.write(content)


def _read_file(path: Path, encoding: str = "utf-8") -> str:
    """Read file content with specified encoding."""
    with open(path, "rt", encoding=encoding) as f:
        return f.read()


def frontmatter_metadata_extractor(text: str) -> tuple[dict, str]:
    """
    Extract metadata from document text using frontmatter.

    Args:
        text: Document text potentially containing frontmatter

    Returns:
        Tuple of (metadata dictionary, content without frontmatter)
    """
    return frontmatter.parse(text)


_SAMPLE_DOC_1 = """\
---
title: Open Source Community
description: Learn how Starlight can help you build greener documentation sites and reduce your carbon footprint.
centeredHeader: true
pubDate: "2020-01-19"
---

import CalenderButton from "../../../components/development-pages/calenderbutton.astro";
import TimeZoneCalendar from "../../../components/development-pages/time-zone-calendar.tsx";
import Welcome from "../../../components/development-pages/Welcome.astro";
import GithubButton from "../../../components/mdx-cards/buttons/github-button.astro";
import Calendar from "../../../components/development-pages/calendarModal.astro";

<Welcome />

## Getting started with contributing

This is the starting point for joining and contributing to building Akash Network - committing code, writing docs, testing product features & reporting bugs, organizing meetups, suggesting ideas for new features, and more.

The Akash Network community welcomes contributions from all skill levels. If you’re interested in contributing, visit our [project list](https://github.com/orgs/akash-network/projects) to find a project that matches your skillset.

<Calendar />
"""

_SAMPLE_DOC_2 = """\
---
title: "Akash Network Documentation"
linkTitle: "Documentation"
description: "Access comprehensive documentation to guide you through using Akash Network. Find detailed instructions, FAQs, and resources for a seamless experience."
categories: ["Documentation"]
---

Welcome to the Akash Network Documentation!

## Getting Started

New to Akash? Start here:

- **[What is Akash Network?](/docs/getting-started/what-is-akash)** - Learn about decentralized cloud computing
- **[Core Concepts](/docs/getting-started/core-concepts)** - Understand how Akash works
- **[Quick Start](/docs/getting-started/quick-start)** - Deploy your first app in under 10 minutes

## Documentation Sections

### Developers

Deploy applications and build on Akash Network:

- **[Getting Started](/docs/developers/getting-started)** - Choose your deployment method and get started
- **[Deployment](/docs/developers/deployment)** - Console, CLI, SDKs, SDL, and AuthZ
- **[Contributing](/docs/developers/contributing)** - Contribute to Akash codebase and documentation
"""

_SAMPLE_CHUNK_1 = {
    "chunk": '```markdown\n## What is a Deployment?\n\nA deployment is your application running on the Akash Network. When you \ncreate a deployment, you\'re requesting compute resources (CPU, RAM, storage) \nfrom providers on the network.\n\nThink of it like renting a server, but:\n- Pay only for what you use (per-block pricing)\n- Choose from multiple providers bidding on your request\n- Your app runs in an isolated container\n```\n\n### For Developers (Technical Users)\n\n**Audience:** Developers integrating Akash\n\n**Requirements:**\n- Assume CLI/programming familiarity\n- Focus on concepts and integration patterns\n- Provide multi-language examples (curl, Go, TypeScript)\n- Link to detailed API reference\n- Show best practices and common patterns\n- Include error handling\n\n**Tone:** Professional, technical, concise\n\n**Example:**\n```markdown\n## Query Providers via gRPC\n\nThe provider query service returns all registered providers and their attributes.\n\n\\```go\nclient, _ := provider.NewQueryClient(conn)\nres, _ := client.Providers(context.Background(), &provider.QueryProvidersRequest{})\n\\```\n\nFilter by attribute:\n\\```go\nreq := &provider.QueryProvidersRequest{\n    Filters: &provider.ProviderFilters{\n        Attributes: []*v1beta3.Attribute{\n            {Key: "region", Value: "us-west"},\n        },\n    },\n}\n\\```\n```\n\n### For Providers (System Administrators)\n\n**Audience:** DevOps engineers, system administrators\n\n**Requirements:**\n- Assume Linux/Kubernetes knowledge\n- Be precise with commands and versions\n- Include all prerequisites\n- Provide verification steps\n- Add comprehensive troubleshooting\n- Emphasize security best practices\n- Provide automated solutions first, manual as fallback\n\n**Tone:** Direct, technical, security-conscious\n\n**Example:**\n```markdown\n## STEP 3: Configure Persistent Storage\n\nInstall Rook-Ceph for persistent storage classes (beta1, beta2, beta3).\n\n**Prerequisites:**\n- Dedicated drives (not partitions) on each worker node\n- Minimum 4 SSDs or 2 NVMe SSDs across cluster\n- Drives mus',
    "index": 13000,
    "path": "DOCUMENTATION_AI_GUIDE.md",
    "metadata": {},
}

_SAMPLE_CHUNK_2 = {
    "chunk": 'Providers(context.Background(), &provider.QueryProvidersRequest{})\n\\```\n\nFilter by attribute:\n\\```go\nreq := &provider.QueryProvidersRequest{\n    Filters: &provider.ProviderFilters{\n        Attributes: []*v1beta3.Attribute{\n            {Key: "region", Value: "us-west"},\n        },\n    },\n}\n\\```\n```\n\n### For Providers (System Administrators)\n\n**Audience:** DevOps engineers, system administrators\n\n**Requirements:**\n- Assume Linux/Kubernetes knowledge\n- Be precise with commands and versions\n- Include all prerequisites\n- Provide verification steps\n- Add comprehensive troubleshooting\n- Emphasize security best practices\n- Provide automated solutions first, manual as fallback\n\n**Tone:** Direct, technical, security-conscious\n\n**Example:**\n```markdown\n## STEP 3: Configure Persistent Storage\n\nInstall Rook-Ceph for persistent storage classes (beta1, beta2, beta3).\n\n**Prerequisites:**\n- Dedicated drives (not partitions) on each worker node\n- Minimum 4 SSDs or 2 NVMe SSDs across cluster\n- Drives must be unformatted\n\n\\```bash\n# Verify available drives (should show no filesystem)\nlsblk -f\n\n# Expected: Empty FSTYPE column for target drives\n\\```\n\n**Important:** Do not use system drives or shared partitions. Rook-Ceph \nrequires exclusive access to raw block devices.\n```\n\n### For Node Operators (Blockchain Engineers)\n\n**Audience:** Blockchain node operators, validators\n\n**Requirements:**\n- Assume blockchain experience\n- Focus on node operations and security\n- Document upgrade procedures clearly\n- Include monitoring and alerting\n- Separate architecture (for devs) from operations (for ops)\n- Provide recovery procedures\n\n**Tone:** Technical, security-focused, precise\n\n**Example:**\n```markdown\n## Validator Security with TMKMS\n\nTMKMS (Tendermint Key Management System) separates your validator key \nfrom the node, adding a critical security layer.\n\n**Architecture:**\n- Validator node runs on Akash (no private key)\n- TMKMS runs on local machine (holds private key)\n- Stunnel provides encrypted c',
    "index": 14000,
    "path": "DOCUMENTATION_AI_GUIDE.md",
    "metadata": {},
}
