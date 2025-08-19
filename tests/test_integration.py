"""
Integration tests for the Sphinx Notion Builder functionality.
"""

from collections.abc import Callable
from pathlib import Path

from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import Paragraph as UnoParagraph

from .helpers import assert_rst_converts_to_paragraphs


def test_single_paragraph_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Single paragraph converts to Notion JSON.
    """
    rst_content = """
        Test Document
        =============

        This is a simple paragraph for testing.
    """

    expected_paragraphs = [
        UnoParagraph(text="This is a simple paragraph for testing.")
    ]

    assert_rst_converts_to_paragraphs(
        rst_content=rst_content,
        expected_paragraphs=expected_paragraphs,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_paragraphs_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple paragraphs in convert to separate Notion blocks.
    """
    rst_content = """
        Multi-Paragraph Document
        ========================

        First paragraph with some text.

        Second paragraph with different content.

        Third paragraph to test multiple blocks.
    """

    expected_paragraphs = [
        UnoParagraph(text="First paragraph with some text."),
        UnoParagraph(text="Second paragraph with different content."),
        UnoParagraph(text="Third paragraph to test multiple blocks."),
    ]

    assert_rst_converts_to_paragraphs(
        rst_content=rst_content,
        expected_paragraphs=expected_paragraphs,
        make_app=make_app,
        tmp_path=tmp_path,
    )
