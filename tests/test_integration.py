"""
Integration tests for the Sphinx Notion Builder functionality.
"""

import json
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pydantic
from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import BulletedItem as UnoBulletedItem
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
from ultimate_notion.obj_api.enums import CodeLang
from ultimate_notion.rich_text import text


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
        assert isinstance(obj_ref, pydantic.BaseModel)
        dumped_block: dict[str, Any] = obj_ref.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
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
    Test that multiline block quotes convert to Notion Quote blocks.
    """
    rst_content = """
        Regular paragraph.

            This is a multiline
            block quote with
            multiple lines.

        Another paragraph.
    """
    expected_objects: list[NotionObject[Any]] = [
        UnoParagraph(text="Regular paragraph."),
        UnoQuote(
            text="This is a multiline\nblock quote with\nmultiple lines."
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
        UnoCode(
            text='def hello():\n    print("Hello, world!")',
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
        UnoCode(text="$ pip install example", language=CodeLang.SHELL),
        UnoCode(text='console.log("hello");', language=CodeLang.JAVASCRIPT),
        UnoCode(text='echo "test"', language=CodeLang.BASH),
        UnoCode(text="Some plain text", language=CodeLang.PLAIN_TEXT),
        UnoCode(text="Code with no language", language=CodeLang.PLAIN_TEXT),
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
