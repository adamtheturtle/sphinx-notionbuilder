"""
Integration tests for the Sphinx Notion Builder functionality.
"""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import Paragraph as UnoParagraph
from ultimate_notion.rich_text import text

from .helpers import assert_rst_converts_to_notion_objects

if TYPE_CHECKING:
    from ultimate_notion.core import NotionObject


def test_single_paragraph_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Single paragraph converts to Notion JSON.
    """
    rst_content = """
        This is a simple paragraph for testing.
    """

    expected_objects: list[NotionObject[Any]] = [
        UnoParagraph(text="This is a simple paragraph for testing.")
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
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
        First paragraph with some text.

        Second paragraph with different content.

        Third paragraph to test multiple blocks.
    """

    expected_objects: list[NotionObject[Any]] = [
        UnoParagraph(text="First paragraph with some text."),
        UnoParagraph(text="Second paragraph with different content."),
        UnoParagraph(text="Third paragraph to test multiple blocks."),
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_inline_formatting_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Inline formatting (bold, italic, code) converts to rich text.
    """
    rst_content = """
        This is **bold** and *italic* and ``inline code``.
    """

    # Create expected rich text with formatting
    normal_text = text("This is ")
    bold_text = text("bold", bold=True)
    normal_text2 = text(" and ")
    italic_text = text("italic", italic=True)
    normal_text3 = text(" and ")
    code_text = text("inline code", code=True)
    normal_text4 = text(".")

    combined_text = (
        normal_text
        + bold_text
        + normal_text2
        + italic_text
        + normal_text3
        + code_text
        + normal_text4
    )

    expected_paragraph = UnoParagraph(text="dummy")
    expected_paragraph.rich_text = combined_text

    expected_objects: list[NotionObject[Any]] = [expected_paragraph]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )
