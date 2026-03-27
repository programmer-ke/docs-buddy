"""Docs Buddy domain objects

Includes:
- Domain entities and services
- Events
- Commands
"""

from dataclasses import dataclass, asdict
from typing import Any, Sequence, Iterator
import json

from docs_buddy import common


@dataclass(frozen=True)
class RawDocument:
    """Representation of an unprocessed document"""

    content: str
    path: str

    @classmethod
    def fromstring(cls, text: str) -> "RawDocument":
        dict_ = json.loads(text)
        return cls(**dict_)

    def __str__(self):
        return json.dumps(asdict(self))


@dataclass(frozen=True)
class AnnotatedDocument:
    """Representation of a document annotated with metadata"""

    content: str
    path: str
    metadata: dict[str, Any]

    @classmethod
    def fromstring(cls, text: str) -> "AnnotatedDocument":
        dict_ = json.loads(text)
        return cls(**dict_)

    def __str__(self):
        return json.dumps(asdict(self), default=common.json_datetime_handler)


@dataclass(frozen=True)
class DocumentChunk:
    """Representation of a chunk of a document"""

    chunk: str
    index: int
    path: str
    metadata: dict[str, Any]

    def __str__(self):
        return json.dumps(asdict(self))


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
