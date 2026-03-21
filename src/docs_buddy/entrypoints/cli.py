from pathlib import Path
import functools

from docs_buddy import adapters, services

frontmatter_annotate_document = functools.partial(
    services.annotate_document,
    metadata_extractor=adapters.frontmatter_metadata_extractor,
)

if __name__ == "__main__":
    repository_id = "akash-network/website"
    akash_website_url = f"https://github.com/{repository_id}.git"
    akash_documentation_prefix = akash_website_url.removesuffix(".git") + "/tree/main"
    repo_destination = Path(".repos") / repository_id
    repo_storage = adapters.FileSystemRepoStorage(repo_destination)
    services.sync_repository(akash_website_url, repo_storage)

    documents_destination = Path(".docs") / repository_id
    docs_storage = adapters.FileSystemDocsStorage(
        repo_destination, documents_destination
    )
    services.update_document_artifacts(
        docs_storage, processor=services.process_raw_document
    )

    annotated_destination = Path(".annotated") / repository_id
    docs_storage = adapters.FileSystemDocsStorage(
        documents_destination, annotated_destination, doc_extensions=("json",)
    )
    services.update_document_artifacts(
        docs_storage, processor=frontmatter_annotate_document
    )
