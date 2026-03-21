"""Docs buddy adapters reside here"""

from contextlib import contextmanager
from typing import Iterator
from pathlib import Path
import subprocess
import shutil
import tempfile

import frontmatter

from docs_buddy.common import PathLike


# todo: add __raw__ to custom classes?
class FakeRepoStorage:
    """Manages repository updates"""

    def __init__(self, target: PathLike):
        self.target = target
        self.fake_is_cloned: bool
        self.fake_can_clone: bool
        self.actions: list = []

    def is_already_cloned(self) -> bool:
        return self.fake_is_cloned

    def can_clone(self) -> bool:
        return self.fake_can_clone

    def clone_repo(self, url: str) -> None:
        self.actions.append(("CLONE", url, self.target))

    def pull_repo(self):
        self.actions.append(("PULL",))


class FileSystemRepoStorage:
    """Manages repository updates"""

    def __init__(self, target):
        self.target = target

    def is_already_cloned(self) -> bool:
        return self._is_git_repository(self.target)

    def pull_repo(self):
        self._update_repository(self.target)

    def clone_repo(self, url: str) -> None:
        self._clone_repository(url, self.target)

    def can_clone(self):
        """Indicates whether we can clone a new repo in the target

        Valid conditions:
        - The target location doesn't exist (git will create it)
        - The target location is an empty directory
        """
        path = Path(self.target)
        return not path.exists() or self._is_empty_dir(path)

    @staticmethod
    def _is_empty_dir(path: Path) -> bool:
        return path.is_dir() and not any(path.iterdir())

    @staticmethod
    def _is_git_repository(directory: str) -> bool:
        git_dir = Path(directory) / ".git"
        return git_dir.exists() and git_dir.is_dir()

    @staticmethod
    def _clone_repository(url: str, target_dir: str) -> None:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, target_dir],
            check=True,
            capture_output=True,
        )

    @staticmethod
    def _update_repository(directory: str) -> None:
        subprocess.run(["git", "pull"], cwd=directory, check=True, capture_output=True)


class FakeDocsStorage:
    """In-memory test implementation of DocsStorage protocol"""

    def __init__(self, source: PathLike, destination: PathLike):
        self.destination = Path(destination)
        self.actions: list = []
        self.read_paths: set = set()
        self.source = Path(source)

        self.sources = {
            "src/content/Docs/index.md": SAMPLE_DOC_2,
            "src/content/Development_Page/welcome/index.mdx": SAMPLE_DOC_1,
        }

        self.sink: dict = {}

    @contextmanager
    def get_temp_location(self):
        temp_location = str(self.destination) + ".tmp"
        self.sink[temp_location] = {}
        self.actions.append(("MKDIR", temp_location))
        try:
            yield temp_location
        finally:
            self.sink.pop(temp_location, None)

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
        self.sink[str(base_dir)][str(path)] = content

    def replace_destination(self, temp_location: PathLike) -> None:
        self.sink[str(self.destination)] = self.sink.pop(temp_location)
        self.actions.append(("RMRF", str(self.destination)))
        self.actions.append(("MV", str(temp_location), str(self.destination)))

    @property
    def destination_sink(self):
        return self.sink[str(self.destination)]


class FileSystemDocsStorage:
    """FileSystem implementation of DocsStorage protocol"""

    def __init__(
        self,
        source: PathLike,
        destination: PathLike,
        doc_extensions: tuple[str, ...] = ("mdx", "md"),
    ):
        self.destination = Path(destination)
        self.source = Path(source)
        self.doc_extensions = doc_extensions

    @contextmanager
    def get_temp_location(self, prefix=""):
        with tempfile.TemporaryDirectory(
            prefix=(prefix or f"{self.destination.name}_")
        ) as temp_dir:
            yield Path(temp_dir)

    def get_source_paths(self) -> Iterator[PathLike]:
        source_directory_prefix = str(self.source) + "/"
        documentation_paths = (
            p
            for ext in self.doc_extensions
            for p in Path(self.source).rglob(f"*.{ext}")
        )
        for full_path in documentation_paths:
            nested_path = str(full_path).removeprefix(source_directory_prefix)
            yield nested_path

    def read_from_source(self, nested_path: PathLike) -> str:
        full_path = Path(self.source) / nested_path
        return self._read_file(full_path)

    def write_to_location(
        self, content: str, path: PathLike, base_dir: PathLike
    ) -> None:
        full_path = Path(base_dir) / path
        self._write_file(full_path, content)

    def replace_destination(self, temp_location: PathLike) -> None:
        """Replaces the destination with the provided temp_location"""

        temp_path = Path(temp_location)
        dest_path = self.destination

        if dest_path.exists():
            shutil.rmtree(dest_path)

        shutil.move(str(temp_path), str(dest_path))

    @staticmethod
    def _is_empty_dir(path: Path) -> bool:
        return path.is_dir() and not any(path.iterdir())

    @staticmethod
    def _read_file(path: Path, encoding: str = "utf-8") -> str:
        with open(path, "rt", encoding=encoding) as f:
            return f.read()

    @staticmethod
    def _write_file(path: Path, content: str, encoding: str = "utf-8") -> None:
        with open(path, "wt", encoding=encoding) as f:
            f.write(content)


def frontmatter_metadata_extractor(text: str) -> tuple[dict, str]:
    """Extract metadata using python-frontmatter"""

    return frontmatter.parse(text)


SAMPLE_DOC_1 = """\
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

SAMPLE_DOC_2 = """\
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
