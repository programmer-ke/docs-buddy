"""Whoosh-based Lexical document index"""

from typing import Iterator
from pathlib import Path
import json

from docs_buddy.common import PathLike, json_datetime_handler, DocsBuddyError
from docs_buddy import domain
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, KEYWORD
from whoosh import qparser


class WhooshIndexError(DocsBuddyError):
    pass


class WhooshDocumentIndex:
    """Whoosh-based implementation of DocumentIndex protocol."""

    _SCHEMA = Schema(
        chunk_id=ID(stored=True, unique=True),
        content=TEXT(stored=True),
        path=ID(stored=True),
        path_keywords=KEYWORD(lowercase=True, scorable=True),
        metadata=TEXT(stored=True),
    )
    _SEARCH_FIELDS = ["content", "metadata", "path_keywords"]

    def __init__(self, index_location: PathLike | None = None):
        """
        Initialize a Whoosh document index.

        """
        self._index = None
        if index_location:
            self._index = index.open_dir(index_location)
            self._query_parser = qparser.MultifieldParser(
                self._SEARCH_FIELDS,
                schema=self._SCHEMA,
                group=qparser.OrGroup,
            )

    def fit(
        self, chunks: Iterator[domain.DocumentChunk], destination: PathLike
    ) -> None:
        """
        Create/update a Whoosh index from DocumentChunks at destination.

        Args:
            chunks: Iterator of DocumentChunk objects to index
            destination: Path where the index should be stored
        """
        ix = index.create_in(str(destination), self._SCHEMA)

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

    def search(self, query: domain.Query, max_results: int) -> list[domain.QueryResult]:
        """Search the whoosh index"""

        if not self._index:
            # todo: consider refactoring index into builder and searcher for better
            # interface segregation. Would help avoid this error
            cls_name = type(self).__name__
            raise WhooshIndexError(
                f"Index not properly initialized. Initialize {cls_name} with index location"
            )

        parsed_query = self._query_parser.parse(str(query))

        with self._index.searcher() as searcher:
            # todo: consider interaction between indexing and searching
            # is locking required for coordination?
            results = searcher.search(parsed_query, limit=max_results)
            results = [
                domain.QueryResult(
                    content=r["content"],
                    path=r["path"],
                    metadata=json.loads(r["metadata"]),
                )
                for r in results
            ]
        return results
