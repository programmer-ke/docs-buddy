import json
from docs_buddy import domain


def test_raw_document_serialization() -> None:
    d = domain.RawDocument(content="foo", path="bar")
    assert str(d) == json.dumps({"content": "foo", "path": "bar"})


def test_annotated_document_serialization() -> None:
    d = domain.AnnotatedDocument(
        content="foo", path="bar", metadata={"title": "foo", "author": "bar"}
    )
    assert str(d) == json.dumps(
        {"content": "foo", "path": "bar", "metadata": {"title": "foo", "author": "bar"}}
    )
