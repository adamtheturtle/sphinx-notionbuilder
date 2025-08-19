"""
Integration tests for the Sphinx Notion Builder functionality.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import Paragraph as UnoParagraph


def test_single_paragraph_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Test that a single paragraph RST file is correctly converted to Notion
    JSON.

    This test creates a simple RST file with one paragraph, builds it
    using the Notion builder, and verifies that the output JSON matches
    what would be expected from Ultimate Notion Paragraph objects.
    """
    # Create source directory and conf.py
    srcdir = tmp_path / "src"
    srcdir.mkdir()

    conf_py_content = """
extensions = ["sphinx_notionbuilder"]
"""
    (srcdir / "conf.py").write_text(data=conf_py_content)

    # Create a simple RST file with one paragraph
    rst_content = """Test Document
=============

This is a simple paragraph for testing.
"""
    (srcdir / "index.rst").write_text(data=rst_content)

    # Build the documentation
    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
    )
    app.build()

    # Find the generated JSON file
    build_dir = tmp_path / "build"
    json_files = list(build_dir.rglob(pattern="*.json"))
    assert len(json_files) > 0, "No JSON files created"
    output_file = json_files[0]

    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    # Create expected Ultimate Notion objects
    expected_paragraph = UnoParagraph(
        text="This is a simple paragraph for testing."
    )

    # Convert to expected JSON format using the same method as the builder
    expected_json = [
        expected_paragraph.obj_ref.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
    ]

    # Compare the structures
    assert generated_json == expected_json
    assert len(generated_json) == 1
    assert generated_json[0]["type"] == "paragraph"
    paragraph_str = json.dumps(obj=generated_json[0])
    assert "This is a simple paragraph for testing." in paragraph_str


def test_multiple_paragraphs_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Test that multiple paragraphs in an RST file are correctly converted.

    This test creates an RST file with multiple paragraphs and verifies
    that each paragraph is converted to a separate Notion Paragraph
    block.
    """
    # Create source directory and conf.py
    srcdir = tmp_path / "src"
    srcdir.mkdir()

    conf_py_content = """
extensions = ["sphinx_notionbuilder"]
"""
    (srcdir / "conf.py").write_text(data=conf_py_content)

    # Create RST file with multiple paragraphs
    rst_content = """Multi-Paragraph Document
========================

First paragraph with some text.

Second paragraph with different content.

Third paragraph to test multiple blocks.
"""
    (srcdir / "index.rst").write_text(data=rst_content)

    # Build the documentation
    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
    )
    app.build()

    # Find the generated JSON file
    build_dir = tmp_path / "build"
    json_files = list(build_dir.rglob(pattern="*.json"))
    assert len(json_files) > 0, "No JSON files created"
    output_file = json_files[0]

    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    # Create expected Ultimate Notion objects
    expected_paragraphs = [
        UnoParagraph(text="First paragraph with some text."),
        UnoParagraph(text="Second paragraph with different content."),
        UnoParagraph(text="Third paragraph to test multiple blocks."),
    ]

    # Convert to expected JSON format
    expected_json = []
    for paragraph in expected_paragraphs:
        dumped_block = paragraph.obj_ref.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
        expected_json.append(dumped_block)

    # Compare the structures
    assert generated_json == expected_json
    expected_paragraph_count = 3
    assert len(generated_json) == expected_paragraph_count

    # Verify each paragraph block
    expected_texts = [
        "First paragraph with some text.",
        "Second paragraph with different content.",
        "Third paragraph to test multiple blocks.",
    ]
    for i, block in enumerate(iterable=generated_json):
        assert block["type"] == "paragraph"
        expected_text = expected_texts[i]
        block_str = json.dumps(obj=block)
        assert expected_text in block_str


def test_empty_document_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Test that an empty RST document (with only title) produces empty JSON.

    This test verifies the behavior when there are no paragraph blocks
    to convert.
    """
    # Create source directory and conf.py
    srcdir = tmp_path / "src"
    srcdir.mkdir()

    conf_py_content = """
extensions = ["sphinx_notionbuilder"]
"""
    (srcdir / "conf.py").write_text(data=conf_py_content)

    # Create RST file with only a title, no content paragraphs
    rst_content = """Empty Document
==============
"""
    (srcdir / "index.rst").write_text(data=rst_content)

    # Build the documentation
    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
    )
    app.build()

    # Find the generated JSON file
    build_dir = tmp_path / "build"
    json_files = list(build_dir.rglob(pattern="*.json"))
    assert len(json_files) > 0, "No JSON files created"
    output_file = json_files[0]

    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    # Should be an empty list since there are no paragraphs
    assert generated_json == []


def test_paragraph_with_inline_formatting(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Test paragraph conversion with inline formatting elements.

    This test verifies that paragraphs with bold, italic, and other
    inline formatting are converted correctly, with the formatting
    flattened to text.
    """
    # Create source directory and conf.py
    srcdir = tmp_path / "src"
    srcdir.mkdir()

    conf_py_content = """
extensions = ["sphinx_notionbuilder"]
"""
    (srcdir / "conf.py").write_text(data=conf_py_content)

    # Create RST file with inline formatting
    rst_content = """Formatted Document
==================

This paragraph has **bold text** and *italic text* in it.
"""
    (srcdir / "index.rst").write_text(data=rst_content)

    # Build the documentation
    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
    )
    app.build()

    # Find the generated JSON file
    build_dir = tmp_path / "build"
    json_files = list(build_dir.rglob(pattern="*.json"))
    assert len(json_files) > 0, "No JSON files created"
    output_file = json_files[0]

    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    # Create expected Ultimate Notion object
    # The astext() method should flatten formatting to plain text
    expected_text = "This paragraph has bold text and italic text in it."
    expected_paragraph = UnoParagraph(text=expected_text)

    # Convert to expected JSON format
    expected_json = [
        expected_paragraph.obj_ref.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
    ]

    # Compare the structures
    assert generated_json == expected_json
    assert len(generated_json) == 1
    assert generated_json[0]["type"] == "paragraph"

    # Verify the text content (formatting should be flattened)
    generated_text_content = json.dumps(obj=generated_json[0])
    assert "bold text" in generated_text_content
    assert "italic text" in generated_text_content
