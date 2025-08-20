"""
Integration tests for the Sphinx Notion Builder functionality.
"""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import (
    BulletedItem as UnoBulletedItem,
)
from ultimate_notion.blocks import (
    Heading1 as UnoHeading1,
)
from ultimate_notion.blocks import (
    Heading2 as UnoHeading2,
)
from ultimate_notion.blocks import (
    Heading3 as UnoHeading3,
)
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
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

    normal_text = text(text="This is ")
    bold_text = text(text="bold", bold=True)
    normal_text2 = text(text=" and ")
    italic_text = text(text="italic", italic=True)
    normal_text3 = text(text=" and ")
    code_text = text(text="inline code", code=True)
    normal_text4 = text(text=".")

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


def test_single_heading_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Single heading converts to Heading 1 block.
    """
    rst_content = """
        Main Title
        ==========

        This is content under the title.
    """

    expected_objects: list[NotionObject[Any]] = [
        UnoHeading1(text="Main Title"),
        UnoParagraph(text="This is content under the title."),
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_heading_levels_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple heading levels convert to appropriate Notion heading blocks.
    """
    rst_content = """
        Main Title
        ==========

        Content under main title.

        Section Title
        -------------

        Content under section.

        Subsection Title
        ~~~~~~~~~~~~~~~~

        Content under subsection.
    """

    expected_objects: list[NotionObject[Any]] = [
        UnoHeading1(text="Main Title"),
        UnoParagraph(text="Content under main title."),
        UnoHeading2(text="Section Title"),
        UnoParagraph(text="Content under section."),
        UnoHeading3(text="Subsection Title"),
        UnoParagraph(text="Content under subsection."),
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_heading_with_formatting_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Headings with inline formatting convert to rich text in heading blocks.
    """
    rst_content = """
        **Bold** and *Italic* Title
        ============================

        Content follows.
    """

    bold_text = text(text="Bold", bold=True)
    normal_text = text(text=" and ")
    italic_text = text(text="Italic", italic=True)
    normal_text2 = text(text=" Title")

    combined_text = bold_text + normal_text + italic_text + normal_text2

    expected_heading = UnoHeading1(text="dummy")
    expected_heading.rich_text = combined_text

    expected_objects: list[NotionObject[Any]] = [
        expected_heading,
        UnoParagraph(text="Content follows."),
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_link_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Simple links convert to rich text with href.
    """
    rst_content = """
        This paragraph contains a `link to example <https://example.com>`_.
    """

    normal_text1 = text(text="This paragraph contains a ")
    link_text = text(text="link to example", href="https://example.com")
    normal_text2 = text(text=".")

    combined_text = normal_text1 + link_text + normal_text2

    expected_paragraph = UnoParagraph(text="dummy")
    expected_paragraph.rich_text = combined_text

    expected_objects: list[NotionObject[Any]] = [expected_paragraph]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_links_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple links in a paragraph convert correctly.
    """
    # Write proper RST content to file to avoid Python string escaping issues
    rst_file = tmp_path / "test_content.rst"
    content = (
        "Visit `Google <https://google.com>`_ and "
        "`GitHub <https://github.com>`_\ntoday."
    )
    rst_file.write_text(data=content)
    rst_content = rst_file.read_text()

    normal_text1 = text(text="Visit ")
    link_text1 = text(text="Google", href="https://google.com")
    normal_text2 = text(text=" and ")
    link_text2 = text(text="GitHub", href="https://github.com")
    normal_text3 = text(text="\ntoday.")

    combined_text = (
        normal_text1 + link_text1 + normal_text2 + link_text2 + normal_text3
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


def test_link_in_heading_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Links in headings convert to rich text with href.
    """
    rst_content = """
        Check out `Notion API <https://developers.notion.com>`_
        ========================================================

        Content follows.
    """

    normal_text1 = text(text="Check out ")
    link_text = text(text="Notion API", href="https://developers.notion.com")

    combined_text = normal_text1 + link_text

    expected_heading = UnoHeading1(text="dummy")
    expected_heading.rich_text = combined_text

    expected_objects: list[NotionObject[Any]] = [
        expected_heading,
        UnoParagraph(text="Content follows."),
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_mixed_formatting_with_links_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Links mixed with other formatting work correctly.
    """
    rst_content = """
        This has **bold** and a `link <https://example.com>`_ and *italic*.
    """

    normal_text1 = text(text="This has ")
    bold_text = text(text="bold", bold=True)
    normal_text2 = text(text=" and a ")
    link_text = text(text="link", href="https://example.com")
    normal_text3 = text(text=" and ")
    italic_text = text(text="italic", italic=True)
    normal_text4 = text(text=".")

    combined_text = (
        normal_text1
        + bold_text
        + normal_text2
        + link_text
        + normal_text3
        + italic_text
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


def test_unnamed_link_with_backticks_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Unnamed links with backticks convert to rich text with href.

    The text should be just the URL without angle brackets.
    """
    rst_content = """
        Visit `<https://example.com>`_ for more information.
    """

    normal_text1 = text(text="Visit ")
    link_text = text(text="https://example.com", href="https://example.com")
    normal_text2 = text(text=" for more information.")

    combined_text = normal_text1 + link_text + normal_text2

    expected_paragraph = UnoParagraph(text="dummy")
    expected_paragraph.rich_text = combined_text

    expected_objects: list[NotionObject[Any]] = [expected_paragraph]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_bulleted_list_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Simple bulleted list converts to BulletedItem blocks.
    """
    rst_content = """
        * First item
        * Second item
        * Third item
    """

    expected_objects: list[NotionObject[Any]] = [
        UnoBulletedItem(text="First item"),
        UnoBulletedItem(text="Second item"),
        UnoBulletedItem(text="Third item"),
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_bulleted_list_with_formatting_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Bulleted list items with formatting (bold, italic, code) convert correctly.
    """
    rst_content = """
        * **Bold** item
        * *Italic* item
        * ``Code`` item
        * Mixed **bold** and *italic* item
    """

    # First item: **Bold** item
    bold_text1 = text(text="Bold", bold=True)
    normal_text1 = text(text=" item")
    combined_text1 = bold_text1 + normal_text1
    expected_item1 = UnoBulletedItem(text="dummy")
    expected_item1.rich_text = combined_text1

    # Second item: *Italic* item
    italic_text2 = text(text="Italic", italic=True)
    normal_text2 = text(text=" item")
    combined_text2 = italic_text2 + normal_text2
    expected_item2 = UnoBulletedItem(text="dummy")
    expected_item2.rich_text = combined_text2

    # Third item: ``Code`` item
    code_text3 = text(text="Code", code=True)
    normal_text3 = text(text=" item")
    combined_text3 = code_text3 + normal_text3
    expected_item3 = UnoBulletedItem(text="dummy")
    expected_item3.rich_text = combined_text3

    # Fourth item: Mixed **bold** and *italic* item
    normal_text4a = text(text="Mixed ")
    bold_text4 = text(text="bold", bold=True)
    normal_text4b = text(text=" and ")
    italic_text4 = text(text="italic", italic=True)
    normal_text4c = text(text=" item")
    combined_text4 = (
        normal_text4a
        + bold_text4
        + normal_text4b
        + italic_text4
        + normal_text4c
    )
    expected_item4 = UnoBulletedItem(text="dummy")
    expected_item4.rich_text = combined_text4

    expected_objects: list[NotionObject[Any]] = [
        expected_item1,
        expected_item2,
        expected_item3,
        expected_item4,
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_nested_bulleted_list_conversion(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Nested bulleted lists convert to BulletedItem blocks with children.
    """
    rst_content = """
        * First item

          * Nested item 1

            * Deep nested item 1
            * Deep nested item 2

          * Nested item 2

        * Second item

          * Another nested item
    """

    # Create deep nested items for nested item 1
    deep_nested_item_1 = UnoBulletedItem(text="Deep nested item 1")
    deep_nested_item_2 = UnoBulletedItem(text="Deep nested item 2")

    # Create nested item 1 with deep children
    nested_item_1 = UnoBulletedItem(text="Nested item 1")
    type_data_class = type(nested_item_1.obj_ref.bulleted_list_item)
    nested_item_1.obj_ref.bulleted_list_item = type_data_class(
        rich_text=nested_item_1.obj_ref.bulleted_list_item.rich_text,
        color=nested_item_1.obj_ref.bulleted_list_item.color,
        children=[deep_nested_item_1.obj_ref, deep_nested_item_2.obj_ref],
    )

    # Create nested item 2 (no children)
    nested_item_2 = UnoBulletedItem(text="Nested item 2")

    # Create first item with children
    first_item = UnoBulletedItem(text="First item")
    first_item.obj_ref.bulleted_list_item = type_data_class(
        rich_text=first_item.obj_ref.bulleted_list_item.rich_text,
        color=first_item.obj_ref.bulleted_list_item.color,
        children=[nested_item_1.obj_ref, nested_item_2.obj_ref],
    )

    # Create nested item for second item
    another_nested_item = UnoBulletedItem(text="Another nested item")

    # Create second item with children
    second_item = UnoBulletedItem(text="Second item")
    second_item.obj_ref.bulleted_list_item = type_data_class(
        rich_text=second_item.obj_ref.bulleted_list_item.rich_text,
        color=second_item.obj_ref.bulleted_list_item.color,
        children=[another_nested_item.obj_ref],
    )

    expected_objects: list[NotionObject[Any]] = [
        first_item,
        second_item,
    ]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_empty_list_item(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Edge case: List item with no text content.
    """
    # Create a custom RST file that forces an empty list item
    rst_file = tmp_path / "test_content.rst"
    content = "* \n"  # Empty bullet point
    rst_file.write_text(data=content)
    rst_content = rst_file.read_text()

    # Should create a BulletedItem with empty text
    expected_objects: list[NotionObject[Any]] = [UnoBulletedItem(text="")]

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_nested_list_with_non_list_item_children(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Nested list items can have non-list item children.
    """
    # Complex RST that might create edge case structures
    rst_content = """
        * Item 1

          .. note:: This is a note within a list

          * Item 2

        * Item 3
    """

    expected_objects: list[NotionObject[Any]] = []

    assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )
