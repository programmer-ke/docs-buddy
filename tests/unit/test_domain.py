import json
import datetime
from docs_buddy import domain


def test_raw_document_serialization() -> None:
    d = domain.RawDocument(content="foo", path="bar")
    assert str(d) == json.dumps({"content": "foo", "path": "bar"})


def test_initialize_raw_document_from_string() -> None:
    raw_doc_str = json.dumps({"content": "foo", "path": "bar"})
    raw_doc = domain.RawDocument.from_raw_text(raw_doc_str)
    assert raw_doc.content == "foo"
    assert raw_doc.path == "bar"


def test_annotated_document_serialization() -> None:
    d = domain.AnnotatedDocument(
        content="foo", path="bar", metadata={"title": "foo", "author": "bar"}
    )
    assert str(d) == json.dumps(
        {"content": "foo", "path": "bar", "metadata": {"title": "foo", "author": "bar"}}
    )


def test_annotated_document_datetime_serialization() -> None:
    d = domain.AnnotatedDocument(
        content="foo",
        path="bar",
        metadata={"title": "foo", "date": datetime.date(2026, 3, 21)},
    )
    assert str(d) == json.dumps(
        {
            "content": "foo",
            "path": "bar",
            "metadata": {"title": "foo", "date": "2026-03-21"},
        }
    )

    d = domain.AnnotatedDocument(
        content="foo",
        path="bar",
        metadata={
            "title": "foo",
            "date": datetime.datetime(2026, 3, 21, 11, 38, 53, 0),
        },
    )
    assert str(d) == json.dumps(
        {
            "content": "foo",
            "path": "bar",
            "metadata": {"title": "foo", "date": "2026-03-21T11:38:53"},
        }
    )
