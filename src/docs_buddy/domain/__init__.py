"""Docs Buddy domain objects

Domain entities, events and commands reside here.
"""

from dataclasses import dataclass, asdict
import json


@dataclass(frozen=True)
class RawDocument:
    """Representation of an unprocessed document"""

    content: str
    path: str

    def __str__(self):
        return json.dumps(asdict(self))


@dataclass(frozen=True)
class AnnotatedDocument:
    """Representation of a document annotated with metadata"""

    content: str
    path: str
    metadata: dict

    def __str__(self):
        return json.dumps(asdict(self))
