from pathlib import Path
from docs_buddy.adapters import FileSystemRepoStorage, FileSystemDocsStorage
from docs_buddy.services import sync_repository, extract_documentation


if __name__ == "__main__":
    repository_id = "akash-network/website"
    akash_website_url = f"https://github.com/{repository_id}.git"
    akash_documentation_prefix = akash_website_url.removesuffix(".git") + "/tree/main"
    repo_destination = Path(".repos") / repository_id
    repo_storage = FileSystemRepoStorage(repo_destination)
    sync_repository(akash_website_url, repo_storage)
    documents_destination = Path(".docs") / repository_id
    docs_storage = FileSystemDocsStorage(repo_destination, documents_destination)
    extract_documentation(docs_storage)
