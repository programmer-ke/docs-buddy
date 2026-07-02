"""This module implements the CLI functionality"""

from pathlib import Path
import os
import argparse
import logging
import sys
import textwrap

from docs_buddy import adapters, services, domain
from docs_buddy.services import commands
from docs_buddy.entrypoints import bootstrap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Return the XDG data directory"""
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        base = Path(xdg_data_home)
    else:
        base = Path.home() / ".local" / "share"
    return base / "docs-buddy"


def main() -> None:
    """CLI main entrypoint"""

    parser = argparse.ArgumentParser(description="Docs Buddy CLI")

    parser.add_argument(
        "--repo-id",
        action="append",
        dest="repo_ids",
        default=[],
        help="Repository ID(s). Can be used multiple times, each time for a different ID",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--update-sources",
        action="store_true",
        help="Update document sources from repository and recreate index",
    )
    group.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Query string to search the documentation",
    )

    args = parser.parse_args()

    # Require at least one repository ID
    if not args.repo_ids:
        parser.error("at least one --repo-id is required")

    data_dir = _get_data_dir()

    if args.update_sources:
        for repository_id in args.repo_ids:
            website_url = f"https://github.com/{repository_id}.git"

            message_bus = bootstrap.get_message_bus(
                repository_storage_path=data_dir / "repos" / repository_id,
                chunks_storage_path=data_dir / "chunks" / repository_id,
                lexical_index_storage_path=data_dir / "whoosh" / repository_id,
            )

            sync_repo_command = commands.SyncRepo(website_url)
            message_bus.send(sync_repo_command)

    elif args.query:
        # todo: Use the first repo ID for search (multi-repo search not yet implemented)
        repo_id = args.repo_ids[0]

        index_path = data_dir / "whoosh" / repo_id
        if not index_path.exists():
            log.error("No index found for %s. Run --update-sources first", repo_id)
            sys.exit(1)

        document_index = adapters.WhooshDocumentIndex(index_location=index_path)

        try:
            query = domain.Query(args.query)
        except domain.InvalidQueryError as exc:
            log.error("Invalid query detected: %s", exc)
            sys.exit(1)

        base_url = f"https://github.com/{repo_id}/blob/main/"

        tools = [adapters.make_search_tool(document_index)]

        system_prompt = textwrap.dedent("""\
        You are a documentation assistant equipped to answer user queries
        by searching the docs.
        """)

        research_user_query = adapters.make_openai_research_agent(system_prompt)

        response = services.find_answer(query, research_user_query, tools)

        print("Docs Buddy Response:\n")
        print(response.answer)
        print("\nReferences:\n")
        for path in response.citations:
            print(f"{base_url}{path}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
