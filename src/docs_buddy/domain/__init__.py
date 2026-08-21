"""Domain Entities and Domain Services"""

from dataclasses import dataclass, asdict
from typing import Any, Sequence, Iterator, TypeAlias, Self
import json

from docs_buddy import common


class InvalidQueryError(common.DocsBuddyError):
    pass


class JSONSerializable:
    """Mixin for JSON serializable dataclasses"""

    @classmethod
    def fromstring(cls, text: str) -> Self:
        dict_ = json.loads(text)
        return cls(**dict_)

    def __str__(self):
        return json.dumps(asdict(self), default=common.json_datetime_handler)


@dataclass(frozen=True)
class RawDocument(JSONSerializable):
    """Representation of an unprocessed document"""

    content: str
    path: str


@dataclass(frozen=True)
class AnnotatedDocument(JSONSerializable):
    """Representation of a document annotated with metadata"""

    content: str
    path: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DocumentChunk(JSONSerializable):
    """Representation of a chunk of a document"""

    chunk: str
    index: int
    path: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Query:
    """Representation of a user query"""

    text: str

    def __post_init__(self):
        clean_query = self.text.strip()
        if not clean_query:
            raise InvalidQueryError(
                f"Invalid query: '{clean_query}'. Length must be > 0 after stripping"
            )
        super().__setattr__("text", clean_query)

    def __str__(self):
        return self.text


@dataclass(frozen=True)
class QueryResult(JSONSerializable):
    """Result of an index query"""

    content: str
    path: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class QueryResponse(JSONSerializable):
    """Structured response for a user query"""

    answer: str
    citations: list[str]

    def __repr__(self):
        cls_name = type(self).__name__
        return f"{cls_name}({self.answer!r}, {self.citations!r})"


def sliding_window(seq: Sequence, size: int, step: int) -> Iterator[dict]:
    """Returns chunks from the sequence"""
    return ({"chunk": seq[i : i + size], "index": i} for i in range(0, len(seq), step))


def overlapping_chunks(text: str, size: int = 2000, step: int = 1000) -> Iterator[dict]:
    """Returns overlapping chunks of text from the provided text"""
    if step < 1 or step >= size:
        raise ValueError(
            f"step ({step}) must be less than size ({size}) and greater than 0 for overlapping chunks"
        )
    return sliding_window(text, size, step)


DocumentArtifact: TypeAlias = RawDocument | AnnotatedDocument | DocumentChunk
