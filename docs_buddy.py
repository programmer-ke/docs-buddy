"""Akash Docs Buddy

An AI agent helping you navigate Akash's documentation with ease.

Major functionality

- Updating retrieved documentation from the Github Repository
- Indexing the documentation
- Answer queries from the documentation
"""

import subprocess
from pathlib import Path
from urllib.parse import urlparse


def sync_repository(url: str, target_dir: str):
    is_already_cloned = is_git_repository(target_dir)
    if is_already_cloned:
        update_repository(target_dir)
    else:
        clone_repository(url, target_dir)


def clone_repository(url: str, target_dir: str):
    subprocess.run(
        ["git", "clone", "--depth", "1", url, target_dir],
        check=True,
        capture_output=True,
    )


def is_git_repository(directory: str) -> bool:
    git_dir = Path(directory) / ".git"
    return git_dir.exists() and git_dir.is_dir()


def update_repository(directory: str):
    subprocess.run(["git", "pull"], cwd=directory, check=True, capture_output=True)


def extract_github_repo_suffix(url: str) -> str:
    """
    Extracts the repository suffix from a Github URL

    >>> ssh_url = "git@github.com:programmer-ke/akash-docs-buddy.git"
    >>> extract_github_repo_suffix(ssh_url)
    'programmer-ke/akash-docs-buddy'
    >>>
    >>> https_url = "https://github.com/programmer-ke/akash-docs-buddy.git"
    >>> extract_github_repo_suffix(https_url)
    'programmer-ke/akash-docs-buddy'
    """
    parsed = urlparse(url)
    is_ssh = parsed.netloc == "" and "@" in parsed.path
    if is_ssh:
        _, suffix = parsed.path.split(":")
    else:
        # https
        suffix = parsed.path.lstrip("/")
    return suffix.strip(".git")


if __name__ == "__main__":
    akash_website_url = "https://github.com/akash-network/website.git"
    destination = Path("/tmp") / extract_github_repo_suffix(akash_website_url)
    sync_repository(akash_website_url, str(destination))
