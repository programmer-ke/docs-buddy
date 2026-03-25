import json
import datetime
import pytest
from docs_buddy import domain


def test_raw_document_serialization() -> None:
    d = domain.RawDocument(content="foo", path="bar")
    assert str(d) == json.dumps({"content": "foo", "path": "bar"})


def test_initialize_raw_document_from_string() -> None:
    raw_doc_str = json.dumps({"content": "foo", "path": "bar"})
    raw_doc = domain.RawDocument.fromstring(raw_doc_str)
    assert raw_doc.content == "foo"
    assert raw_doc.path == "bar"


def test_initialize_annotated_doc_from_string() -> None:
    raw_str = json.dumps(
        {"content": "foo", "path": "bar", "metadata": {"title": "foo", "author": "bar"}}
    )
    annotated_doc = domain.AnnotatedDocument.fromstring(raw_str)
    assert annotated_doc.content == "foo"
    assert annotated_doc.path == "bar"
    assert annotated_doc.metadata == {"title": "foo", "author": "bar"}


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


def test_overlapping_chunks_basic() -> None:
    text = "abcdefghij"
    result = list(domain.overlapping_chunks(text, size=4, step=2))
    assert result == [
        {"index": 0, "chunk": "abcd"},
        {"index": 2, "chunk": "cdef"},
        {"index": 4, "chunk": "efgh"},
        {"index": 6, "chunk": "ghij"},
        {"index": 8, "chunk": "ij"},
    ]


def test_overlapping_chunks_exact_fit() -> None:
    """Test when text length fits chunk size exactly."""
    text = "123456"
    result = list(domain.overlapping_chunks(text, size=3, step=2))
    assert result == [
        {"index": 0, "chunk": "123"},
        {"index": 2, "chunk": "345"},
        {"index": 4, "chunk": "56"},
    ]


def test_overlapping_chunks_default_params() -> None:
    """Test with default size and step."""
    text = "a" * 5000  # Longer than default size
    result = list(domain.overlapping_chunks(text))
    # Should create chunks of 2000 chars with 1000 overlap
    assert len(result) > 1
    assert all(len(item["chunk"]) == 2000 for item in result[:-1])
    # Last chunk may be shorter
    assert len(result[-1]["chunk"]) <= 2000


def test_overlapping_chunks_no_overlap_raises() -> None:
    """Test that equal step and size raises ValueError."""
    with pytest.raises(ValueError, match="step.*must be less than size"):
        domain.overlapping_chunks("abc", size=3, step=3)


def test_overlapping_chunks_gap_raises() -> None:
    """Test that step > size raises ValueError."""
    with pytest.raises(ValueError, match="step.*must be less than size"):
        domain.overlapping_chunks("abc", size=2, step=3)


def test_overlapping_chunks_empty_text() -> None:
    """Test with empty input string."""
    result = list(domain.overlapping_chunks("", size=3, step=2))
    assert result == []


def test_overlapping_chunks_smaller_than_size() -> None:
    """Test when text is smaller than chunk size."""
    text = "abc"
    result = list(domain.overlapping_chunks(text, size=5, step=2))
    assert result == [{"index": 0, "chunk": "abc"}, {"index": 2, "chunk": "c"}]


def test_overlapping_chunks_overlap_amount() -> None:
    """Verify overlap amount is correct."""
    text = "0123456789"
    result = list(domain.overlapping_chunks(text, size=5, step=3))
    # Overlap = size - step = 5 - 3 = 2 characters
    assert result == [
        {"index": 0, "chunk": "01234"},
        {"index": 3, "chunk": "34567"},
        {"index": 6, "chunk": "6789"},
        {"index": 9, "chunk": "9"},
    ]
    # Check overlap between first two chunks
    assert result[0]["chunk"][-2:] == result[1]["chunk"][:2]  # "34"
    # Check overlap between second and third chunks
    assert result[1]["chunk"][-2:] == result[2]["chunk"][:2]  # "67"


def test_overlapping_chunks_unicode_support() -> None:
    """Test with Unicode characters."""
    text = "🎉🎊🎈🎁🎂"
    result = list(domain.overlapping_chunks(text, size=3, step=2))
    # Each emoji is one Unicode character
    assert result == [
        {"index": 0, "chunk": "🎉🎊🎈"},
        {"index": 2, "chunk": "🎈🎁🎂"},
        {"index": 4, "chunk": "🎂"},
    ]


def test_overlapping_chunks_newlines_preserved() -> None:
    """Test that newlines are preserved in chunks."""
    text = "line1\nline2\nline3"
    result = list(domain.overlapping_chunks(text, size=10, step=5))

    # Newlines should remain in first 3 chunks
    assert all(["\n" in item["chunk"] for item in result[:3]])
