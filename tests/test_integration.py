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

from .helpers import assert_paragraphs_match_json


def test_single_paragraph_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Single paragraph converts to Notion JSON.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="")

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
        confoverrides={"extensions": ["sphinx_notionbuilder"]},
    )
    app.build()

    output_file = app.outdir / "index.json"

    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    expected_paragraphs = [
        UnoParagraph(text="This is a simple paragraph for testing.")
    ]

    assert_paragraphs_match_json(
        expected_paragraphs=expected_paragraphs,
        generated_json=generated_json,
    )


def test_multiple_paragraphs_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple paragraphs in convert to separate Notion blocks.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="")

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
        confoverrides={"extensions": ["sphinx_notionbuilder"]},
    )
    app.build()

    output_file = app.outdir / "index.json"

    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    expected_paragraphs = [
        UnoParagraph(text="First paragraph with some text."),
        UnoParagraph(text="Second paragraph with different content."),
        UnoParagraph(text="Third paragraph to test multiple blocks."),
    ]

    assert_paragraphs_match_json(
        expected_paragraphs=expected_paragraphs,
        generated_json=generated_json,
    )
