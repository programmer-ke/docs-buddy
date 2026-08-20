import pytest
from docs_buddy import adapters, services, domain


def test_can_create_search_tool_over_index() -> None:
    # Given an index built from a fake pipeline
    source = ".chunks/programmmer-ke/akash-docs-buddy"
    dest = ".index/programmer-ke/akash-docs-buddy"
    pipeline = adapters.FakeDocumentChunksPipeline(source, dest)
    index = adapters.FakeIndex(pipeline, dest)
    services.index_document_chunks(pipeline, index)

    repo_description = "The foo website documentation in markdown"
    tool_id = "github_com_programmer_ke_docs_buddy"
    search_index_tool = adapters.make_search_tool(index, tool_id, repo_description)

    # when we check description, it contains the repo information
    tool_doc = search_index_tool.__doc__
    assert tool_doc and repo_description in tool_doc

    # when we check the tool name, it contains the tool id
    assert tool_id in search_index_tool.__name__

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
