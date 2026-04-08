"""Whoosh-based Lexical document index"""

from typing import Iterator
from pathlib import Path
import json

from docs_buddy.common import PathLike, json_datetime_handler
from docs_buddy import domain
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, KEYWORD


class WhooshDocumentIndex:
    """Whoosh-based implementation of DocumentIndex protocol."""

    def __init__(self):
        """
        Initialize a Whoosh document index.

        """

        self._schema = Schema(
            chunk_id=ID(stored=True, unique=True),
            content=TEXT(stored=True),
            path=ID(stored=True),
            path_keywords=KEYWORD(lowercase=True, scorable=True),
            metadata=TEXT(stored=True),
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
        ix = index.create_in(str(destination), self._schema)

        writer = ix.writer()

        for chunk in chunks:

            # Create a unique ID for each chunk (path + index)
            chunk_id = f"{chunk.path}_{chunk.index}"

            writer.add_document(
                chunk_id=chunk_id,
                content=chunk.chunk,
                path=chunk.path,
                path_keywords=chunk.path.split("/"),
                metadata=json.dumps(chunk.metadata, default=json_datetime_handler),
            )

        writer.commit()
