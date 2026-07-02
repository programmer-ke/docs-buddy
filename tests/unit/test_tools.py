import pytest
from docs_buddy import adapters, services, domain


def test_can_create_search_tool_over_index() -> None:
    # Given an index built from a fake pipeline
    source = ".chunks/programmmer-ke/akash-docs-buddy"
    dest = ".index/programmer-ke/akash-docs-buddy"
    pipeline = adapters.FakeDocumentChunksPipeline(source, dest)
    index = adapters.FakeIndex(pipeline)
    services.index_document_chunks(pipeline, index)

    search_index_tool = adapters.make_search_tool(index)
    phrase = "provider"

    # When we search without a limit
    results = search_index_tool(phrase)
    # Then we get at least one result
    assert len(results) > 0

    # When we request exactly one result
    results = search_index_tool(phrase, max_results=1)
    # Then exactly one result is returned
    assert len(results) == 1

    # When max_results is <= 0, then an error is raised
    bad_values = [0, -1, -30]
    for bad_value in bad_values:
        with pytest.raises(adapters.ToolError):
            _ = search_index_tool(phrase, max_results=bad_value)

    # When search phrase is invalid, then an error is raised
    bad_phrases = ["", "  ", "\t"]
    for phrase in bad_phrases:
        with pytest.raises(domain.InvalidQueryError):
            _ = search_index_tool(phrase)
