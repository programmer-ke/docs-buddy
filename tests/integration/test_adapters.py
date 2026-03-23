from docs_buddy import adapters

SAMPLE_DOC_1 = """\
---
title: Open Source Community
description: Learn how Starlight can help you build greener documentation sites and reduce your carbon footprint.
centeredHeader: true
pubDate: "2020-01-19"
---
## Getting started with contributing

This is the starting point for joining and contributing to building Akash Network - committing code, writing docs, testing product features & reporting bugs, organizing meetups, suggesting ideas for new features, and more.
"""


def test_frontmatter_extractor() -> None:
    metadata, content = adapters.frontmatter_metadata_extractor(SAMPLE_DOC_1)

    assert all([t in metadata for t in ['title', 'description', 'centeredHeader', 'pubDate']])
    assert metadata["title"] == "Open Source Community"
    assert metadata['pubDate'] == '2020-01-19'
    assert SAMPLE_DOC_1.strip().endswith(content)
