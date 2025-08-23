"""
Integration tests for the Sphinx Notion Builder functionality.
"""

import json
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sphinx.testing.util import SphinxTestApp
from ultimate_notion import Emoji
from ultimate_notion.blocks import BulletedItem as UnoBulletedItem
from ultimate_notion.blocks import Callout as UnoCallout
from ultimate_notion.blocks import Code as UnoCode
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
from ultimate_notion.blocks import (
    Quote as UnoQuote,
)
from ultimate_notion.blocks import (
    TableOfContents as UnoTableOfContents,
)
from ultimate_notion.core import NotionObject
from ultimate_notion.obj_api.core import GenericObject
from ultimate_notion.obj_api.enums import CodeLang, Color
from ultimate_notion.rich_text import text


def _create_code_block_without_annotations(
    content: str, language: CodeLang
) -> UnoCode:
    """Create a code block without annotations to match the fixed behavior.

    This matches the fix in visit_literal_block where annotations are
    removed to prevent white text color in code blocks.
    """
    # Create rich text and remove annotations to match the fix
    code_text = text(text=content)
    # Remove annotations to prevent white text in code blocks
    del code_text.rich_texts[0].obj_ref.annotations  # pyright: ignore[reportUnknownMemberType]

    # Create code block and set the rich text
    code_block = UnoCode(text="dummy", language=language)
    code_block.rich_text = code_text
    return code_block


def _assert_rst_converts_to_notion_objects(
    rst_content: str,
    expected_objects: list[NotionObject[Any]],
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    The given rST content is converted to the given expected objects.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="")

    cleaned_content = textwrap.dedent(text=rst_content).strip()
    (srcdir / "index.rst").write_text(data=cleaned_content)

    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
        confoverrides={"extensions": ["sphinx_notion"]},
    )
    app.build()

    output_file = app.outdir / "index.json"
    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    expected_json: list[dict[str, Any]] = []
    for notion_object in expected_objects:
        obj_ref = notion_object.obj_ref
        assert isinstance(obj_ref, GenericObject)
        dumped_block = obj_ref.serialize_for_api()
        expected_json.append(dumped_block)

    assert generated_json == expected_json, (generated_json, expected_json)


def test_single_paragraph(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_paragraphs(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_inline_formatting(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_single_heading(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_heading_levels(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_heading_with_formatting(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_link(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_links(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple links in a paragraph convert correctly.
    """
    # Write proper rST content to file to avoid Python string escaping issues
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_link_in_heading(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_mixed_formatting_with_links(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_unnamed_link_with_backticks(
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

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_quote(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that block quotes convert to Notion Quote blocks.
    """
    rst_content = """
        Regular paragraph.

            This is a block quote.

        Another paragraph.
    """
    expected_objects: list[NotionObject[Any]] = [
        UnoParagraph(text="Regular paragraph."),
        UnoQuote(text="This is a block quote."),
        UnoParagraph(text="Another paragraph."),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiline_quote(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that multi-line block quotes convert to Notion Quote blocks.
    """
    rst_content = """
        Regular paragraph.

            This is a multi-line
            block quote with
            multiple lines.

        Another paragraph.
    """
    expected_objects: list[NotionObject[Any]] = [
        UnoParagraph(text="Regular paragraph."),
        UnoQuote(
            text="This is a multi-line\nblock quote with\nmultiple lines."
        ),
        UnoParagraph(text="Another paragraph."),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_table_of_contents(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that contents directive converts to Notion TableOfContents blocks.
    """
    rst_content = """
        Introduction
        ============

        .. contents::

        First Section
        -------------

        Content here.

        Second Section
        --------------

        More content.
    """
    expected_objects: list[NotionObject[Any]] = [
        UnoHeading1(text="Introduction"),
        UnoTableOfContents(),
        UnoHeading2(text="First Section"),
        UnoParagraph(text="Content here."),
        UnoHeading2(text="Second Section"),
        UnoParagraph(text="More content."),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_code_block(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Code blocks convert to Notion Code blocks.
    """
    rst_content = """
        Regular paragraph.

        .. code-block:: python

           def hello():
               print("Hello, world!")

        Another paragraph.
    """
    expected_objects: list[NotionObject[Any]] = [
        UnoParagraph(text="Regular paragraph."),
        _create_code_block_without_annotations(
            content='def hello():\n    print("Hello, world!")',
            language=CodeLang.PYTHON,
        ),
        UnoParagraph(text="Another paragraph."),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_code_block_language_mapping(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that various languages map correctly.
    """
    rst_content = """
        .. code-block:: console

           $ pip install example

        .. code-block:: javascript

           console.log("hello");

        .. code-block:: bash

           echo "test"

        .. code-block:: text

           Some plain text

        .. code-block::

           Code with no language
    """
    expected_objects: list[NotionObject[Any]] = [
        _create_code_block_without_annotations(
            content="$ pip install example", language=CodeLang.SHELL
        ),
        _create_code_block_without_annotations(
            content='console.log("hello");', language=CodeLang.JAVASCRIPT
        ),
        _create_code_block_without_annotations(
            content='echo "test"', language=CodeLang.BASH
        ),
        _create_code_block_without_annotations(
            content="Some plain text", language=CodeLang.PLAIN_TEXT
        ),
        _create_code_block_without_annotations(
            content="Code with no language", language=CodeLang.PLAIN_TEXT
        ),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_flat_bullet_list(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that flat bullet lists convert correctly to Notion BulletedItem.
    """
    rst_content = """
        * First bullet point
        * Second bullet point
        * Third bullet point with longer text
    """
    expected_objects: list[NotionObject[Any]] = [
        UnoBulletedItem(text="First bullet point"),
        UnoBulletedItem(text="Second bullet point"),
        UnoBulletedItem(text="Third bullet point with longer text"),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_bullet_list_with_inline_formatting(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test bullet lists with inline formatting.
    """
    rst_content = """
        * This is **bold text** in a bullet
    """
    bullet = UnoBulletedItem(text="placeholder")
    bullet.rich_text = (
        text(text="This is ", bold=False, italic=False, code=False)
        + text(text="bold text", bold=True, italic=False, code=False)
        + text(text=" in a bullet", bold=False, italic=False, code=False)
    )

    expected_objects: list[NotionObject[Any]] = [
        bullet,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


@pytest.mark.parametrize(
    argnames=("admonition_type", "emoji", "color", "message"),
    argvalues=[
        ("note", "📝", Color.BLUE, "This is an important note."),
        ("warning", "⚠️", Color.YELLOW, "This is a warning message."),
        ("tip", "💡", Color.GREEN, "This is a helpful tip."),
    ],
)
def test_admonition_single_line(
    *,
    admonition_type: str,
    emoji: str,
    color: Color,
    message: str,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that admonitions convert to Notion Callout blocks.
    """
    rst_content = f"""
        Regular paragraph.

        .. {admonition_type}:: {message}

        Another paragraph.
    """

    callout = UnoCallout(
        text=message,
        icon=Emoji(emoji=emoji),
        color=color,
    )

    expected_objects: list[NotionObject[Any]] = [
        UnoParagraph(text="Regular paragraph."),
        callout,
        UnoParagraph(text="Another paragraph."),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


@pytest.mark.parametrize(
    argnames=("admonition_type", "emoji", "color"),
    argvalues=[
        ("note", "📝", Color.BLUE),
        ("warning", "⚠️", Color.YELLOW),
        ("tip", "💡", Color.GREEN),
    ],
)
def test_admonition_multiline(
    admonition_type: str,
    emoji: str,
    color: Color,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Test that admonitions with multiple paragraphs work.

    The first paragraph becomes the callout text, and subsequent
    paragraphs become nested blocks within the callout.
    """
    rst_content = f"""
        .. {admonition_type}::
           This is the first paragraph of the {admonition_type}.

           This is the second paragraph that should be nested.
    """
    callout = UnoCallout(text="", icon=Emoji(emoji=emoji), color=color)
    callout.rich_text = text(
        text=f"This is the first paragraph of the {admonition_type}."
    )

    nested_paragraph = UnoParagraph(
        text="This is the second paragraph that should be nested."
    )

    callout.obj_ref.value.children.append(nested_paragraph.obj_ref)  # pyright: ignore[reportUnknownMemberType]

    expected_objects: list[NotionObject[Any]] = [
        callout,
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_admonition_with_code_block(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that admonitions can contain code blocks as nested children.
    """
    rst_content = """
        .. note::
           This note contains a code example.

           .. code-block:: python

              def hello():
                  print("Hello, world!")

           The code above demonstrates a simple function.
    """

    callout = UnoCallout(text="", icon=Emoji(emoji="📝"), color=Color.BLUE)
    callout.rich_text = text(text="This note contains a code example.")

    nested_code_block = _create_code_block_without_annotations(
        content='def hello():\n    print("Hello, world!")',
        language=CodeLang.PYTHON,
    )
    nested_paragraph = UnoParagraph(
        text="The code above demonstrates a simple function."
    )

    callout.obj_ref.value.children.append(nested_code_block.obj_ref)  # pyright: ignore[reportUnknownMemberType]
    callout.obj_ref.value.children.append(nested_paragraph.obj_ref)  # pyright: ignore[reportUnknownMemberType]

    expected_objects: list[NotionObject[Any]] = [
        callout,
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_admonition_with_code_block_first(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Test admonition with code block as first child (not paragraph).

    This tests the else clause when first child is not a paragraph.
    """
    rst_content = """
        .. note::

           .. code-block:: python

              def hello():
                  print("Hello, world!")

           This paragraph comes after the code block.
    """

    callout = UnoCallout(text="", icon=Emoji(emoji="📝"), color=Color.BLUE)
    callout.rich_text = text(text="")

    nested_code_block = _create_code_block_without_annotations(
        content='def hello():\n    print("Hello, world!")',
        language=CodeLang.PYTHON,
    )
    nested_paragraph = UnoParagraph(
        text="This paragraph comes after the code block."
    )

    callout.obj_ref.value.children.append(nested_code_block.obj_ref)  # pyright: ignore[reportUnknownMemberType]
    callout.obj_ref.value.children.append(nested_paragraph.obj_ref)  # pyright: ignore[reportUnknownMemberType]

    expected_objects: list[NotionObject[Any]] = [callout]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_nested_bullet_list(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that nested bullet lists are converted to Notion BulletedItem blocks
    with proper nesting structure (limited to 2 levels).
    """
    rst_content = """
        * Top level item 1
        * Top level item 2 with children

          * Second level item 1
          * Second level item 2

        * Top level item 3
    """

    # Create nested bullet structure with only 2 levels
    # Second level items (no children allowed at this level)
    second_level_1 = UnoBulletedItem(text="Second level item 1")
    second_level_2 = UnoBulletedItem(text="Second level item 2")

    # Top level items
    top_level_1 = UnoBulletedItem(text="Top level item 1")
    top_level_2 = UnoBulletedItem(text="Top level item 2 with children")
    # Add second level children to top level item 2
    # Remove pyright ignore once we have
    # https://github.com/ultimate-notion/ultimate-notion/issues/94.
    top_level_2.obj_ref.value.children.append(second_level_1.obj_ref)  # pyright: ignore[reportUnknownMemberType]
    top_level_2.obj_ref.value.children.append(second_level_2.obj_ref)  # pyright: ignore[reportUnknownMemberType]

    top_level_3 = UnoBulletedItem(text="Top level item 3")

    expected_objects: list[NotionObject[Any]] = [
        top_level_1,
        top_level_2,
        top_level_3,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_nested_bullet_list_error_on_excessive_depth(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that an error is raised when bullet lists exceed the 2-level limit.
    """
    rst_content = """
        * Top level item
        * Top level with children

          * Second level item
          * Second level with children

            * Third level item (should cause error)

        * Another top level item
    """

    expected_message = (
        "Nested bullet point at depth 3 exceeds Notion API limit of 2 levels."
    )
    with pytest.raises(expected_exception=ValueError, match=expected_message):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
        )
