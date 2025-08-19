"""
Integration tests for the Sphinx Notion Builder functionality.
"""

import json
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import Paragraph as UnoParagraph


def test_single_paragraph_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Single paragraph converts to Notion JSON.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()

    conf_py_content = textwrap.dedent(
        text="""
        extensions = ["sphinx_notionbuilder"]
    """
    ).strip()
    (srcdir / "conf.py").write_text(data=conf_py_content)

    rst_content = textwrap.dedent(
        text="""
        Test Document
        =============

        This is a simple paragraph for testing.
    """
    ).strip()
    (srcdir / "index.rst").write_text(data=rst_content)

    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
    )
    app.build()

    build_dir = tmp_path / "build"
    json_files = list(build_dir.rglob(pattern="*.json"))
    assert len(json_files) > 0, "No JSON files created"
    output_file = json_files[0]

    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    expected_paragraph = UnoParagraph(
        text="This is a simple paragraph for testing."
    )

    expected_json = [
        expected_paragraph.obj_ref.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
    ]

    assert generated_json == expected_json


def test_multiple_paragraphs_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple paragraphs in convert to separate Notion blocks.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()

    conf_py_content = textwrap.dedent(
        text="""
        extensions = ["sphinx_notionbuilder"]
    """
    ).strip()
    (srcdir / "conf.py").write_text(data=conf_py_content)

    rst_content = textwrap.dedent(
        text="""
        Multi-Paragraph Document
        ========================

        First paragraph with some text.

        Second paragraph with different content.

        Third paragraph to test multiple blocks.
    """
    ).strip()
    (srcdir / "index.rst").write_text(data=rst_content)

    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
    )
    app.build()

    build_dir = tmp_path / "build"
    json_files = list(build_dir.rglob(pattern="*.json"))
    assert len(json_files) > 0, "No JSON files created"
    output_file = json_files[0]

    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    expected_paragraphs = [
        UnoParagraph(text="First paragraph with some text."),
        UnoParagraph(text="Second paragraph with different content."),
        UnoParagraph(text="Third paragraph to test multiple blocks."),
    ]

    expected_json = []
    for paragraph in expected_paragraphs:
        dumped_block = paragraph.obj_ref.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
        expected_json.append(dumped_block)

    assert generated_json == expected_json
