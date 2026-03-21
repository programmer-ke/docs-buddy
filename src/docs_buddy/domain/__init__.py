"""Docs Buddy domain objects

Domain entities, events and commands reside here.
"""

from dataclasses import dataclass, asdict
import json

from docs_buddy import common


@dataclass(frozen=True)
class RawDocument:
    """Representation of an unprocessed document"""

    content: str
    path: str

    @classmethod
    def from_raw_text(cls, text: str) -> "RawDocument":
        dict_ = json.loads(text)
        return cls(**dict_)

    def __str__(self):
        return json.dumps(asdict(self))


@dataclass(frozen=True)
class AnnotatedDocument:
    """Representation of a document annotated with metadata"""

    content: str
    path: str
    metadata: dict

    def __str__(self):
        return json.dumps(asdict(self), default=common.json_datetime_handler)
