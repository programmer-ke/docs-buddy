"""Whoosh-based Lexical document index"""

from typing import Iterator
from pathlib import Path
import json

from docs_buddy.common import PathLike, json_datetime_handler
from docs_buddy import domain
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, KEYWORD
from whoosh import qparser

_SCHEMA = Schema(
    chunk_id=ID(stored=True, unique=True),
    content=TEXT(stored=True),
    path=ID(stored=True),
    path_keywords=KEYWORD(lowercase=True, scorable=True),
    metadata=TEXT(stored=True),
)

_SEARCH_FIELDS = ["content", "metadata", "path_keywords"]


class WhooshIndexBuilder:
    """Whoosh-based implementation of DocumentIndexBuilder protocol."""

    def fit(
        self, chunks: Iterator[domain.DocumentChunk], destination: PathLike
    ) -> None:
        """
        Create a Whoosh index from DocumentChunks at destination.

        Args:
            chunks: Iterator of DocumentChunk objects to index
            destination: Path where the index should be stored
        """
        ix = index.create_in(str(destination), _SCHEMA)

        writer = ix.writer()

        for chunk in chunks:

            # Create a unique ID for each chunk (path + index)
            chunk_id = f"{chunk.path}_{chunk.index}"

            writer.add_document(
                chunk_id=chunk_id,
                content=chunk.chunk,
                path=chunk.path,
                path_keywords=" ".join(chunk.path.split("/")),
                metadata=json.dumps(chunk.metadata, default=json_datetime_handler),
            )

        writer.commit()


class WhooshIndexSearcher:
    """Whoosh-based implementation of DocumentIndexSearcher protocol."""

    def __init__(self, index_location: PathLike, url_prefix: str | None = None):
        """
        Initialize a Whoosh document index searcher.

        Args:
            index_location: Path to an existing Whoosh index directory.
            url_prefix: Optional URL prefix to prepend to result paths.
        """
        self._index = index.open_dir(str(index_location))
        self._url_prefix = url_prefix
        self._query_parser = qparser.MultifieldParser(
            _SEARCH_FIELDS,
            schema=self._index.schema,
            group=qparser.OrGroup,
        )

    def search(self, query: domain.Query, max_results: int) -> list[domain.QueryResult]:
        """Search the whoosh index"""

        parsed_query = self._query_parser.parse(str(query))

        prefix = ""

        if self._url_prefix:
            prefix = (
                self._url_prefix + "/"
                if not self._url_prefix.endswith("/")
                else self._url_prefix
            )

        with self._index.searcher() as searcher:
            # todo: consider interaction between indexing and searching
            # is locking required for coordination?
            results = searcher.search(parsed_query, limit=max_results)
            results = [
                domain.QueryResult(
                    content=r["content"],
                    path=prefix + r["path"],
                    metadata=json.loads(r["metadata"]),
                )
                for r in results
            ]

        return results
