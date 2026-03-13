import json
from docs_buddy.domain import RawDocument


def test_raw_document_serialization() -> None:
    d = RawDocument(content="foo", path="bar")
    assert str(d) == json.dumps({"content": "foo", "path": "bar"})
