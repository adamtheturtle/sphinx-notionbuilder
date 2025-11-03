"""
Integration tests for the Sphinx Notion Builder functionality.
"""

import base64
import json
import re
import textwrap
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any

import anstrip
import pytest
from beartype import beartype
from sphinx.testing.util import SphinxTestApp
from ultimate_notion import Emoji
from ultimate_notion.blocks import PDF as UnoPDF  # noqa: N811
from ultimate_notion.blocks import Audio as UnoAudio
from ultimate_notion.blocks import Block, ParentBlock
from ultimate_notion.blocks import BulletedItem as UnoBulletedItem
from ultimate_notion.blocks import Callout as UnoCallout
from ultimate_notion.blocks import Code as UnoCode
from ultimate_notion.blocks import Divider as UnoDivider
from ultimate_notion.blocks import Embed as UnoEmbed
from ultimate_notion.blocks import Equation as UnoEquation
from ultimate_notion.blocks import (
    Heading1 as UnoHeading1,
)
from ultimate_notion.blocks import (
    Heading2 as UnoHeading2,
)
from ultimate_notion.blocks import (
    Heading3 as UnoHeading3,
)
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import NumberedItem as UnoNumberedItem
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.blocks import (
    Quote as UnoQuote,
)
from ultimate_notion.blocks import Table as UnoTable
from ultimate_notion.blocks import (
    TableOfContents as UnoTableOfContents,
)
from ultimate_notion.blocks import ToDoItem as UnoToDoItem
from ultimate_notion.blocks import (
    ToggleItem as UnoToggleItem,
)
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.file import ExternalFile
from ultimate_notion.obj_api.enums import BGColor, CodeLang, Color
from ultimate_notion.rich_text import Text, math, text


@beartype
def _details_from_block(
    *,
    block: Block,
) -> dict[str, Any]:
    """
    Create a serialized block details from a Block.
    """
    serialized_obj = block.obj_ref.serialize_for_api()
    if isinstance(block, ParentBlock) and block.children:
        serialized_obj[block.obj_ref.type]["children"] = [
            _details_from_block(block=child) for child in block.children
        ]
    return serialized_obj


@beartype
def _assert_rst_converts_to_notion_objects(
    *,
    rst_content: str,
    expected_objects: list[Block],
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: tuple[str, ...] = ("sphinx_notion",),
    conf_py_content: str = "",
    expected_warnings: Collection[str] = (),
    confoverrides: dict[str, Any] | None = None,
) -> SphinxTestApp:
    """
    ReStructuredText content converts to expected Notion objects via Sphinx
    build process.
    """
    confoverrides = confoverrides or {}
    srcdir = tmp_path / "src"
    srcdir.mkdir(exist_ok=True)

    (srcdir / "conf.py").write_text(data=conf_py_content)

    cleaned_content = textwrap.dedent(text=rst_content).strip()
    (srcdir / "index.rst").write_text(data=cleaned_content)

    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
        confoverrides={"extensions": list(extensions)} | confoverrides,
    )
    app.build()
    assert app.statuscode == 0

    warning_output = app.warning.getvalue()
    ansi_stripped_warning_output = anstrip.strip(string=warning_output)
    warnings = [
        item.strip()
        for item in ansi_stripped_warning_output.split(sep="WARNING: ")
        if item.strip()
    ]
    assert list(expected_warnings) == warnings

    output_file = app.outdir / "index.json"
    with output_file.open(encoding="utf-8") as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    expected_json: list[dict[str, Any]] = [
        _details_from_block(block=expected_object)
        for expected_object in expected_objects
    ]

    assert generated_json == expected_json
    return app


def test_single_paragraph(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Single paragraph becomes Notion paragraph block.
    """
    rst_content = """
        This is a simple paragraph for testing.
    """

    expected_objects: list[Block] = [
        UnoParagraph(text=text(text="This is a simple paragraph for testing."))
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_paragraphs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple paragraphs become separate Notion paragraph blocks.
    """
    rst_content = """
        First paragraph with some text.

        Second paragraph with different content.

        Third paragraph to test multiple blocks.
    """

    expected_objects: list[Block] = [
        UnoParagraph(text=text(text="First paragraph with some text.")),
        UnoParagraph(
            text=text(text="Second paragraph with different content.")
        ),
        UnoParagraph(
            text=text(text="Third paragraph to test multiple blocks.")
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_inline_formatting(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Inline formatting (bold, italic, code) becomes rich text annotations.
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

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_single_heading(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Single heading becomes Heading 1 block.
    """
    rst_content = """
        Main Title
        ==========
    """

    expected_objects: list[Block] = [
        UnoHeading1(text=text(text="Main Title")),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_heading_levels(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple heading levels become appropriate Notion heading blocks.
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

    expected_objects: list[Block] = [
        UnoHeading1(text=text(text="Main Title")),
        UnoParagraph(text=text(text="Content under main title.")),
        UnoHeading2(text=text(text="Section Title")),
        UnoParagraph(text=text(text="Content under section.")),
        UnoHeading3(text=text(text="Subsection Title")),
        UnoParagraph(text=text(text="Content under subsection.")),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_heading_with_formatting(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Headings with inline formatting become rich text in heading blocks.
    """
    rst_content = """
        **Bold** and *Italic* Title
        ============================
    """

    bold_text = text(text="Bold", bold=True)
    normal_text = text(text=" and ")
    italic_text = text(text="Italic", italic=True)
    normal_text2 = text(text=" Title")

    combined_text = bold_text + normal_text + italic_text + normal_text2

    expected_heading = UnoHeading1(text=combined_text)

    expected_objects: list[Block] = [
        expected_heading,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_link(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Simple links become rich text with href attributes.
    """
    rst_content = """
        This paragraph contains a `link to example <https://example.com>`_.
    """

    normal_text1 = text(text="This paragraph contains a ")
    link_text = text(text="link to example", href="https://example.com")
    normal_text2 = text(text=".")

    combined_text = normal_text1 + link_text + normal_text2

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiple_links(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multiple links in a paragraph become separate rich text segments.
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

    expected_paragraph = UnoParagraph(text=combined_text)
    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_link_in_heading(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Links in headings become rich text with href attributes.
    """
    rst_content = """
        Check out `Notion API <https://developers.notion.com>`_
        ========================================================
    """

    normal_text1 = text(text="Check out ")
    link_text = text(text="Notion API", href="https://developers.notion.com")

    combined_text = normal_text1 + link_text

    expected_heading = UnoHeading1(text=combined_text)

    expected_objects: list[Block] = [
        expected_heading,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_mixed_formatting_with_links(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Links mixed with other formatting preserve all annotations.
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

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_unnamed_link_with_backticks(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Unnamed links with backticks become rich text with URL as display text.

    The display text excludes angle brackets from the URL.
    """
    rst_content = """
        Visit `<https://example.com>`_ for more information.
    """

    normal_text1 = text(text="Visit ")
    link_text = text(text="https://example.com", href="https://example.com")
    normal_text2 = text(text=" for more information.")

    combined_text = normal_text1 + link_text + normal_text2

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_quote(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Block quotes become Notion Quote blocks.
    """
    rst_content = """
        Some content.

            This is a block quote.
    """
    expected_objects: list[Block] = [
        UnoParagraph(text=text(text="Some content.")),
        UnoQuote(text=text(text="This is a block quote.")),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multiline_quote(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Multi-line block quotes become single Notion Quote blocks with line breaks.
    """
    rst_content = """
        Some content.

            This is a multi-line
            block quote with
            multiple lines.
    """
    expected_objects: list[Block] = [
        UnoParagraph(text=text(text="Some content.")),
        UnoQuote(
            text=text(
                text="This is a multi-line\nblock quote with\nmultiple lines."
            )
        ),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_multi_paragraph_quote(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Block quotes with multiple paragraphs create Quote blocks with nested
    paragraph children.
    """
    rst_content = """
        Some content.

            This is the first paragraph
            with multiple lines
            in the quote.

            This is a second paragraph
            with **bold text** and multiple
            lines as well.
    """
    quote = UnoQuote(
        text=text(
            text="This is the first paragraph\nwith multiple lines\n"
            "in the quote."
        )
    )

    nested_paragraph = UnoParagraph(
        text=(
            text(text="This is a second paragraph\nwith ")
            + text(text="bold text", bold=True)
            + text(text=" and multiple\nlines as well.")
        )
    )

    quote.append(blocks=[nested_paragraph])

    expected_objects: list[Block] = [
        UnoParagraph(text=text(text="Some content.")),
        quote,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_table_of_contents(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``contents`` directive becomes Notion TableOfContents block.
    """
    rst_content = """
        Introduction
        ============

        .. contents::

        First Section
        -------------

        Second Section
        --------------
    """
    expected_objects: list[Block] = [
        UnoHeading1(text=text(text="Introduction")),
        UnoTableOfContents(),
        UnoHeading2(text=text(text="First Section")),
        UnoHeading2(text=text(text="Second Section")),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_toctree_directive(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``toctree`` directive produces no output as it's for navigation structure.
    """
    rst_content = """
        Introduction
        ============

        .. toctree::
    """

    expected_objects: list[Block] = [
        UnoHeading1(text=text(text="Introduction")),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_code_block(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Code blocks become Notion Code blocks with syntax highlighting.
    """
    rst_content = """
        .. code-block:: python

           def hello():
               print("Hello, world!")
    """
    expected_objects: list[Block] = [
        UnoCode(
            text=text(text='def hello():\n    print("Hello, world!")'),
            language=CodeLang.PYTHON,
        ),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_code_block_language_mapping(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Various languages map to appropriate Notion code block languages.
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
    expected_objects: list[Block] = [
        UnoCode(
            text=text(text="$ pip install example"), language=CodeLang.SHELL
        ),
        UnoCode(
            text=text(text='console.log("hello");'),
            language=CodeLang.JAVASCRIPT,
        ),
        UnoCode(text=text(text='echo "test"'), language=CodeLang.BASH),
        UnoCode(
            text=text(text="Some plain text"), language=CodeLang.PLAIN_TEXT
        ),
        UnoCode(
            text=text(text="Code with no language"),
            language=CodeLang.PLAIN_TEXT,
        ),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_flat_bullet_list(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Flat bullet lists become separate Notion BulletedItem blocks.
    """
    rst_content = """
        * First bullet point
        * Second bullet point
        * Third bullet point with longer text
    """
    expected_objects: list[Block] = [
        UnoBulletedItem(text=text(text="First bullet point")),
        UnoBulletedItem(text=text(text="Second bullet point")),
        UnoBulletedItem(text=text(text="Third bullet point with longer text")),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_bullet_list_with_inline_formatting(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Bullet lists preserve inline formatting in rich text.
    """
    rst_content = """
        * This is **bold text** in a bullet
    """
    bullet = UnoBulletedItem(
        text=(
            text(text="This is ", bold=False, italic=False, code=False)
            + text(text="bold text", bold=True, italic=False, code=False)
            + text(text=" in a bullet", bold=False, italic=False, code=False)
        )
    )

    expected_objects: list[Block] = [
        bullet,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


@pytest.mark.parametrize(
    argnames=("admonition_type", "emoji", "background_color", "message"),
    argvalues=[
        ("note", "📝", BGColor.BLUE, "This is an important note."),
        ("warning", "⚠️", BGColor.YELLOW, "This is a warning message."),
        ("tip", "💡", BGColor.GREEN, "This is a helpful tip."),
        ("attention", "👀", BGColor.YELLOW, "This requires your attention."),
        ("caution", "⚠️", BGColor.YELLOW, "This is a caution message."),
        ("danger", "🚨", BGColor.RED, "This is a danger message."),
        ("error", "❌", BGColor.RED, "This is an error message."),
        ("hint", "💡", BGColor.GREEN, "This is a helpful hint."),
        ("important", "❗", BGColor.RED, "This is important information."),
    ],
)
def test_admonition_single_line(
    *,
    admonition_type: str,
    emoji: str,
    background_color: BGColor,
    message: str,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Admonitions become Notion Callout blocks with appropriate icons and colors.
    """
    rst_content = f"""
        .. {admonition_type}:: {message}
    """

    callout = UnoCallout(
        text=text(text=message),
        icon=Emoji(emoji=emoji),
        color=background_color,
    )

    expected_objects: list[Block] = [
        callout,
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


@pytest.mark.parametrize(
    argnames=("admonition_type", "emoji", "background_color"),
    argvalues=[
        ("note", "📝", BGColor.BLUE),
        ("warning", "⚠️", BGColor.YELLOW),
        ("tip", "💡", BGColor.GREEN),
    ],
)
def test_admonition_multiline(
    *,
    admonition_type: str,
    emoji: str,
    background_color: BGColor,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Admonitions with multiple paragraphs create nested blocks.

    The first paragraph becomes the callout text, and subsequent
    paragraphs become nested blocks within the callout.
    """
    rst_content = f"""
        .. {admonition_type}::
           This is the first paragraph of the {admonition_type}.

           This is the second paragraph that should be nested.
    """
    callout = UnoCallout(
        text=text(
            text=f"This is the first paragraph of the {admonition_type}."
        ),
        icon=Emoji(emoji=emoji),
        color=background_color,
    )

    nested_paragraph = UnoParagraph(
        text=text(text="This is the second paragraph that should be nested.")
    )

    callout.append(blocks=[nested_paragraph])

    expected_objects: list[Block] = [
        callout,
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_admonition_with_code_block(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Admonitions contain code blocks as nested children.
    """
    rst_content = """
        .. note::
           This note contains a code example.

           .. code-block:: python

              def hello():
                  print("Hello, world!")

           The code above demonstrates a simple function.
    """

    callout = UnoCallout(
        text=text(text="This note contains a code example."),
        icon=Emoji(emoji="📝"),
        color=BGColor.BLUE,
    )

    nested_code_block = UnoCode(
        text=text(text='def hello():\n    print("Hello, world!")'),
        language=CodeLang.PYTHON,
    )
    nested_paragraph = UnoParagraph(
        text=text(text="The code above demonstrates a simple function.")
    )

    callout.append(blocks=[nested_code_block])
    callout.append(blocks=[nested_paragraph])

    expected_objects: list[Block] = [
        callout,
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_admonition_with_code_block_first(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Admonition with code block as first child creates empty callout text.

    When the first child is not a paragraph, the callout text remains
    empty.
    """
    rst_content = """
        .. note::

           .. code-block:: python

              def hello():
                  print("Hello, world!")

           This paragraph comes after the code block.
    """

    callout = UnoCallout(
        text=text(text=""),
        icon=Emoji(emoji="📝"),
        color=BGColor.BLUE,
    )

    nested_code_block = UnoCode(
        text=text(text='def hello():\n    print("Hello, world!")'),
        language=CodeLang.PYTHON,
    )
    nested_paragraph = UnoParagraph(
        text=text(text="This paragraph comes after the code block.")
    )

    callout.append(blocks=[nested_code_block])
    callout.append(blocks=[nested_paragraph])

    expected_objects: list[Block] = [callout]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_admonition_with_bullet_points(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Bullet points appear within admonitions as nested blocks (issue #78).
    """
    rst_content = """
        .. note::

           This is an important note that demonstrates the note admonition
           support.

           * A
           * B
    """

    callout = UnoCallout(
        text=text(
            text="This is an important note that demonstrates the note "
            "admonition\nsupport."
        ),
        icon=Emoji(emoji="📝"),
        color=BGColor.BLUE,
    )

    bullet_a = UnoBulletedItem(text=text(text="A"))
    bullet_b = UnoBulletedItem(text=text(text="B"))

    callout.append(blocks=[bullet_a])
    callout.append(blocks=[bullet_b])

    expected_objects: list[Block] = [
        callout,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_generic_admonition(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Generic admonitions set callout text to the first line of the callout.

    Generic admonitions require a title so are different from other
    admonitions.
    """
    rst_content = """
        .. admonition:: Important Information

           This is the first paragraph.

           This is the second paragraph.
    """

    callout = UnoCallout(
        text=text(text="Important Information"),
        icon=Emoji(emoji="💬"),
        color=BGColor.GRAY,
    )

    nested_paragraph1 = UnoParagraph(
        text=text(text="This is the first paragraph.")
    )
    nested_paragraph2 = UnoParagraph(
        text=text(text="This is the second paragraph.")
    )

    callout.append(blocks=[nested_paragraph1])
    callout.append(blocks=[nested_paragraph2])

    expected_objects: list[Block] = [
        callout,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_nested_bullet_list(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Deeply nested bullet lists create hierarchical block structures.
    """
    rst_content = """
        * Top level item
        * Top level with children

          * Second level item
          * Second level with children

            * Third level item (now allowed!)

        * Another top level item
    """

    third_level_1 = UnoBulletedItem(
        text=text(text="Third level item (now allowed!)")
    )

    second_level_1 = UnoBulletedItem(text=text(text="Second level item"))
    second_level_2 = UnoBulletedItem(
        text=text(text="Second level with children")
    )

    top_level_1 = UnoBulletedItem(text=text(text="Top level item"))
    top_level_2 = UnoBulletedItem(text=text(text="Top level with children"))

    second_level_2.append(blocks=[third_level_1])
    top_level_2.append(blocks=[second_level_1])
    top_level_2.append(blocks=[second_level_2])

    top_level_3 = UnoBulletedItem(text=text(text="Another top level item"))

    expected_objects: list[Block] = [
        top_level_1,
        top_level_2,
        top_level_3,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx_toolbox.collapse"),
    )


def test_flat_numbered_list(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Flat numbered lists become separate Notion NumberedItem blocks.
    """
    rst_content = """
        1. First numbered point
        2. Second numbered point
        3. Third numbered point with longer text
    """
    expected_objects: list[Block] = [
        UnoNumberedItem(text=text(text="First numbered point")),
        UnoNumberedItem(text=text(text="Second numbered point")),
        UnoNumberedItem(
            text=text(text="Third numbered point with longer text")
        ),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_numbered_list_with_inline_formatting(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Numbered lists preserve inline formatting in rich text.
    """
    rst_content = """
        1. This is **bold text** in a numbered list
    """
    numbered_item = UnoNumberedItem(
        text=(
            text(text="This is ", bold=False, italic=False, code=False)
            + text(text="bold text", bold=True, italic=False, code=False)
            + text(
                text=" in a numbered list",
                bold=False,
                italic=False,
                code=False,
            )
        )
    )

    expected_objects: list[Block] = [
        numbered_item,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_nested_numbered_list(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Deeply nested numbered lists create hierarchical block structures.
    """
    rst_content = """
        1. Top level item
        2. Top level with children

           1. Second level item
           2. Second level with children

              1. Third level item (now allowed!)

        3. Another top level item
    """

    third_level_1 = UnoNumberedItem(
        text=text(text="Third level item (now allowed!)")
    )

    second_level_1 = UnoNumberedItem(text=text(text="Second level item"))
    second_level_2 = UnoNumberedItem(
        text=text(text="Second level with children")
    )

    top_level_1 = UnoNumberedItem(text=text(text="Top level item"))
    top_level_2 = UnoNumberedItem(text=text(text="Top level with children"))

    second_level_2.append(blocks=[third_level_1])
    top_level_2.append(blocks=[second_level_1])
    top_level_2.append(blocks=[second_level_2])

    top_level_3 = UnoNumberedItem(text=text(text="Another top level item"))

    expected_objects: list[Block] = [
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


def test_collapse_block(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``collapse`` directives become Notion ToggleItem blocks for expandable
    content.
    """
    rst_content = """
        .. collapse:: Click to expand

           This content is hidden by default.

           It supports **formatting**.
    """

    toggle_block = UnoToggleItem(text=text(text="Click to expand"))

    nested_para1 = UnoParagraph(
        text=text(text="This content is hidden by default.")
    )
    nested_para2 = UnoParagraph(
        text=(
            text(text="It supports ", bold=False)
            + text(text="formatting", bold=True)
            + text(text=".", bold=False)
        )
    )

    toggle_block.append(blocks=[nested_para1])
    toggle_block.append(blocks=[nested_para2])

    expected_objects: list[Block] = [
        toggle_block,
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx_toolbox.collapse"),
    )


def test_simple_table(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Simple rST table becomes Notion Table block with header row.
    """
    rst_content = """
        +----------+----------+
        | Header 1 | Header 2 |
        +==========+==========+
        | Cell 1   | Cell 2   |
        +----------+----------+
        | Cell 3   | Cell 4   |
        |          |          |
        | Cell 3   | Cell 4   |
        +----------+----------+
    """

    table = UnoTable(n_rows=3, n_cols=2, header_row=True)
    # Header row
    table[0, 0] = text(text="Header 1")
    table[0, 1] = text(text="Header 2")
    # First data row
    table[1, 0] = text(text="Cell 1")
    table[1, 1] = text(text="Cell 2")
    # Second data row - now creates separate text segments for each paragraph
    table[2, 0] = text(text="Cell 3") + text(text="\n\n") + text(text="Cell 3")
    table[2, 1] = text(text="Cell 4") + text(text="\n\n") + text(text="Cell 4")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_table_without_header_row(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Table without heading row becomes Notion Table block with header_row=False.
    """
    rst_content = """
        +--------+--------+
        | Cell 1 | Cell 2 |
        +--------+--------+
        | Cell 3 | Cell 4 |
        +--------+--------+
    """
    table = UnoTable(n_rows=2, n_cols=2, header_row=False)
    table[0, 0] = text(text="Cell 1")
    table[0, 1] = text(text="Cell 2")
    table[1, 0] = text(text="Cell 3")
    table[1, 1] = text(text="Cell 4")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_table_inline_formatting(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Table headers and cells preserve inline formatting as rich text.
    """
    rst_content = """
        +----------------------+----------------------+
        | **Header Bold**      | *Header Italic*      |
        +======================+======================+
        | ``cell code``        | Normal cell          |
        +----------------------+----------------------+
    """

    table = UnoTable(n_rows=2, n_cols=2, header_row=True)

    table[0, 0] = text(text="Header Bold", bold=True)
    table[0, 1] = text(text="Header Italic", italic=True)

    table[1, 0] = text(text="cell code", code=True)
    table[1, 1] = text(text="Normal cell")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_table_cell_non_paragraph_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Table cells with non-paragraph content raise a clear error message.
    """
    rst_content = """
        +----------+----------+
        | Header 1 | Header 2 |
        +==========+==========+
        | Cell 1   | Cell 2   |
        +----------+----------+
        | Cell 3   | * Item 1 |
        |          | * Item 2 |
        +----------+----------+
    """

    index_rst = tmp_path / "src" / "index.rst"
    expected_message = (
        r"^Notion table cells can only contain paragraph content. "
        r"Found non-paragraph node: bullet_list on line 6 "
        rf"in {re.escape(pattern=str(object=index_rst))}.$"
    )
    with pytest.raises(expected_exception=ValueError, match=expected_message):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
        )


def test_simple_image(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``image`` directives become Notion Image blocks with URL.
    """
    rst_content = """
        .. image:: https://www.example.com/path/to/image.png
    """

    expected_objects: list[Block] = [
        UnoImage(
            file=ExternalFile(url="https://www.example.com/path/to/image.png")
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_image_with_alt_text_only(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``image`` directives with only alt text become Notion Image blocks without
    captions.
    """
    rst_content = """
        .. image:: https://www.example.com/path/to/image.png
           :alt: Example image
    """

    expected_objects: list[Block] = [
        UnoImage(
            file=ExternalFile(url="https://www.example.com/path/to/image.png"),
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_literalinclude_without_caption(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``literalinclude`` directives without captions become code blocks.
    """
    rst_content = """
        .. literalinclude:: conf.py
           :language: python
    """

    conf_py_content = textwrap.dedent(
        text="""
        def hello():
            print("Hello from included file!")
        """,
    )

    expected_objects: list[Block] = [
        UnoCode(
            text=text(text=conf_py_content),
            language=CodeLang.PYTHON,
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        conf_py_content=conf_py_content,
    )


def test_literalinclude_with_caption(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``literalinclude`` directives with captions become code blocks with
    formatted captions.
    """
    rst_content = """
        .. literalinclude:: conf.py
           :language: python
           :caption: **Example** Configuration File
    """

    conf_py_content = textwrap.dedent(
        text="""
        def hello():
            print("Hello from included file!")
        """,
    )

    # Create caption with bold text
    bold_text = text(text="Example", bold=True)
    normal_text = text(text=" Configuration File")
    caption_with_bold = bold_text + normal_text

    expected_objects: list[Block] = [
        UnoCode(
            text=text(text=conf_py_content),
            language=CodeLang.PYTHON,
            caption=caption_with_bold,
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        conf_py_content=conf_py_content,
    )


def test_heading_level_4_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Heading level 4+ raises a clear error message.
    """
    rst_content = """
        Main Title
        ==========

        Section Title
        -------------

        Subsection Title
        ~~~~~~~~~~~~~~~~

        Sub-subsection Title
        ^^^^^^^^^^^^^^^^^^^^

        Content under sub-subsection.
    """

    index_rst = tmp_path / "src" / "index.rst"
    expected_message = (
        r"^Notion only supports heading levels 1-3, but found heading level 4 "
        rf"on line 11 in {re.escape(pattern=str(object=index_rst))}.$"
    )
    with pytest.raises(
        expected_exception=ValueError,
        match=expected_message,
    ):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
        )


def test_local_image_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Local image files are converted to file:// URLs in the JSON output.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    test_image_path = srcdir / "test_image.png"
    png_data = base64.b64decode(
        s="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    test_image_path.write_bytes(data=png_data)

    rst_content = """
        .. image:: test_image.png
    """

    expected_objects: list[Block] = [
        UnoImage(file=ExternalFile(url=test_image_path.as_uri())),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_simple_video(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``video`` directives become Notion Video blocks with URL.
    """
    rst_content = """
        .. video:: https://www.example.com/path/to/video.mp4
    """

    expected_objects: list[Block] = [
        UnoVideo(
            file=ExternalFile(url="https://www.example.com/path/to/video.mp4")
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinxcontrib.video", "sphinx_notion"),
    )


def test_video_with_caption(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Video directives with captions include the caption in the Notion Video
    block.
    """
    rst_content = """
        .. video:: https://www.example.com/path/to/video.mp4
           :caption: Example video
    """

    expected_objects: list[Block] = [
        UnoVideo(
            file=ExternalFile(url="https://www.example.com/path/to/video.mp4"),
            caption=text(text="Example video"),
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinxcontrib.video", "sphinx_notion"),
    )


def test_local_video_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Local video files are converted to file:// URLs in the JSON output.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    test_video_path = srcdir / "test_video.mp4"
    # Create a minimal MP4 file (just some dummy data)
    test_video_path.write_bytes(data=b"fake mp4 content")

    rst_content = """
        .. video:: test_video.mp4
    """

    expected_objects: list[Block] = [
        UnoVideo(file=ExternalFile(url=test_video_path.as_uri())),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinxcontrib.video"),
    )


def test_simple_audio(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    ``audio`` directives become Notion Audio blocks with URL.
    """
    rst_content = """
        .. audio:: https://www.example.com/path/to/audio.mp3
    """

    expected_objects: list[Block] = [
        UnoAudio(
            file=ExternalFile(url="https://www.example.com/path/to/audio.mp3")
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "atsphinx.audioplayer"),
    )


def test_local_audio_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Local audio files are converted to file:// URLs in the JSON output.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    test_audio_path = srcdir / "test_audio.mp3"
    # Create a minimal MP3 file (just some dummy data)
    test_audio_path.write_bytes(data=b"fake mp3 content")

    rst_content = """
        .. audio:: test_audio.mp3
    """

    expected_objects: list[Block] = [
        UnoAudio(file=ExternalFile(url=test_audio_path.as_uri())),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "atsphinx.audioplayer"),
    )


def test_strikethrough_text(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Strikethrough text using
    `sphinxnotes-strike <https://github.com/sphinx-toolbox/sphinxnotes-strike>`_
    becomes rich text with strikethrough formatting.
    """
    rst_content = """
        This text has :strike:`strikethrough` formatting.

        This text has :del:`strikethrough` formatting.
    """

    normal_text1 = text(text="This text has ")
    strikethrough_text = text(text="strikethrough", strikethrough=True)
    normal_text2 = text(text=" formatting.")

    combined_text = normal_text1 + strikethrough_text + normal_text2

    expected_objects: list[Block] = [
        UnoParagraph(text=combined_text),
        UnoParagraph(text=combined_text),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=(
            "sphinxnotes.strike",
            "sphinx_notion",
        ),
    )


def test_comment_ignored(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Comments in reStructuredText are ignored and do not appear in output.
    """
    rst_content = """
        This is a paragraph with content.

        .. This is a comment that should be ignored.
           It can span multiple lines.

        This is another paragraph after the comment.
    """

    expected_objects: list[Block] = [
        UnoParagraph(text=text(text="This is a paragraph with content.")),
        UnoParagraph(
            text=text(text="This is another paragraph after the comment.")
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_list_table_header_one_allowed(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    List table with header-rows option other than 0 raises ValueError.
    """
    rst_content = """
        .. list-table::
           :header-rows: 1

           * - Header 1
             - Header 2
           * - Cell 1
             - Cell 2
    """

    table = UnoTable(n_rows=2, n_cols=2, header_row=True)
    table[0, 0] = text(text="Header 1")
    table[0, 1] = text(text="Header 2")
    table[1, 0] = text(text="Cell 1")
    table[1, 1] = text(text="Cell 2")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_list_table_header_rows_zero_allowed(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    List table with header-rows: 0 should be allowed and processed.
    """
    rst_content = """
        .. list-table::
           :header-rows: 0

           * - Cell 1
             - Cell 2
    """

    table = UnoTable(n_rows=1, n_cols=2, header_row=False)
    table[0, 0] = text(text="Cell 1")
    table[0, 1] = text(text="Cell 2")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_list_table_header_maximum_one_allowed(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    List table with header-rows option other than 0 or 1 emits a warning.
    """
    rst_content = """
        .. list-table::
           :header-rows: 2

           * - Header a 1
             - Header a 2
           * - Header b 1
             - Header b 2
           * - Cell a 1
             - Cell a 2
    """

    expected_warning = (
        "Tables with multiple header rows are not supported. "
        f"First header row is on line 4 in {tmp_path / 'src' / 'index.rst'}, "
        "last header row is on line 6"
    )

    table = UnoTable(n_rows=3, n_cols=2, header_row=True)
    table[0, 0] = text(text="Header a 1")
    table[0, 1] = text(text="Header a 2")
    table[1, 0] = text(text="Header b 1")
    table[1, 1] = text(text="Header b 2")
    table[2, 0] = text(text="Cell a 1")
    table[2, 1] = text(text="Cell a 2")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        expected_warnings=[expected_warning],
    )


def test_list_table_stub_columns_one(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    List table with :stub-columns: 1 creates table with header column.
    """
    rst_content = """
        .. list-table::
           :header-rows: 1
           :stub-columns: 1

           * - Header 1
             - Header 2
             - Header 3
           * - Row 1, Col 1
             - Row 1, Col 2
             - Row 1, Col 3
           * - Row 2, Col 1
             - Row 2, Col 2
             - Row 2, Col 3
    """

    table = UnoTable(n_rows=3, n_cols=3, header_row=True, header_col=True)
    # Header row
    table[0, 0] = text(text="Header 1")
    table[0, 1] = text(text="Header 2")
    table[0, 2] = text(text="Header 3")
    # First data row
    table[1, 0] = text(text="Row 1, Col 1")
    table[1, 1] = text(text="Row 1, Col 2")
    table[1, 2] = text(text="Row 1, Col 3")
    # Second data row
    table[2, 0] = text(text="Row 2, Col 1")
    table[2, 1] = text(text="Row 2, Col 2")
    table[2, 2] = text(text="Row 2, Col 3")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_list_table_stub_columns_two(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    List table with :stub-columns: 2 emits a warning.
    """
    rst_content = """
        .. list-table::
           :header-rows: 1
           :stub-columns: 2

           * - Header 1
             - Header 2
             - Header 3
           * - Row 1, Col 1
             - Row 1, Col 2
             - Row 1, Col 3
           * - Row 2, Col 1
             - Row 2, Col 2
             - Row 2, Col 3
    """

    expected_warning = (
        "Tables with more than 1 stub column are not supported. "
        "Found 2 stub columns on table with first body row on line 8 in "
        f"{tmp_path / 'src' / 'index.rst'}."
    )

    table = UnoTable(n_rows=3, n_cols=3, header_row=True, header_col=True)
    table[0, 0] = text(text="Header 1")
    table[0, 1] = text(text="Header 2")
    table[0, 2] = text(text="Header 3")
    table[1, 0] = text(text="Row 1, Col 1")
    table[1, 1] = text(text="Row 1, Col 2")
    table[1, 2] = text(text="Row 1, Col 3")
    table[2, 0] = text(text="Row 2, Col 1")
    table[2, 1] = text(text="Row 2, Col 2")
    table[2, 2] = text(text="Row 2, Col 3")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        expected_warnings=[expected_warning],
    )


def test_list_table_with_title_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    List table with title emits a warning since Notion tables do not have
    titles.
    """
    rst_content = """
        .. list-table:: My Table Title
           :header-rows: 1

           * - Header 1
             - Header 2
           * - Cell 1
             - Cell 2
    """

    expected_warning = (
        f"Table has a title 'My Table Title' on line 1 in "
        f"{tmp_path / 'src' / 'index.rst'}, "
        "but Notion tables do not have titles."
    )

    table = UnoTable(n_rows=2, n_cols=2, header_row=True)
    table[0, 0] = text(text="Header 1")
    table[0, 1] = text(text="Header 2")
    table[1, 0] = text(text="Cell 1")
    table[1, 1] = text(text="Cell 2")

    expected_objects: list[Block] = [table]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        expected_warnings=[expected_warning],
    )


@pytest.mark.parametrize(
    argnames="extensions",
    argvalues=[
        ("sphinx_notion",),
        ("sphinx_notion", "sphinx_simplepdf"),
        ("sphinx_simplepdf", "sphinx_notion"),
    ],
)
def test_simple_pdf(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: tuple[str, ...],
) -> None:
    """
    ``pdf-include`` directives become Notion PDF blocks with URL.
    """
    rst_content = """
        .. pdf-include:: https://www.example.com/path/to/document.pdf
    """

    expected_objects: list[Block] = [
        UnoPDF(
            file=ExternalFile(
                url="https://www.example.com/path/to/document.pdf"
            )
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=extensions,
    )


def test_pdf_with_options(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    PDF directives with options (width, height) are processed correctly.
    """
    rst_content = """
        .. pdf-include:: https://www.example.com/path/to/document.pdf
           :width: 50%
           :height: 300px
    """

    expected_objects: list[Block] = [
        UnoPDF(
            file=ExternalFile(
                url="https://www.example.com/path/to/document.pdf"
            ),
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion",),
    )


def test_local_pdf_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Local PDF files are converted to file:// URLs in the JSON output.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    test_pdf_path = srcdir / "test_document.pdf"
    # Create a minimal PDF file (just some dummy data)
    test_pdf_path.write_bytes(data=b"fake pdf content")

    rst_content = """
        .. pdf-include:: test_document.pdf
    """

    expected_objects: list[Block] = [
        UnoPDF(file=ExternalFile(url=test_pdf_path.as_uri())),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion",),
    )


@pytest.mark.parametrize(
    argnames="extensions",
    argvalues=[
        ("sphinx_notion", "sphinx_simplepdf"),
        ("sphinx_simplepdf", "sphinx_notion"),
    ],
)
def test_pdf_with_html(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: tuple[str, ...],
) -> None:
    """
    PDF directives with HTML output are processed correctly.
    """
    rst_content = """
        .. pdf-include:: https://www.example.com/path/to/document.pdf
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    test_pdf_path = srcdir / "test_document.pdf"
    # Create a minimal PDF file (just some dummy data)
    test_pdf_path.write_bytes(data=b"fake pdf content")
    (srcdir / "index.rst").write_text(data=rst_content)
    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="html",
        confoverrides={"extensions": list(extensions)},
    )
    app.build()
    assert app.statuscode == 0
    assert not app.warning.getvalue()
    index_html = (tmp_path / "build" / "html" / "index.html").read_text()
    expected_iframe = (
        "<iframe "
        'src="https://www.example.com/path/to/document.pdf" '
        'style="height: 400px; width: 100%">'
        "</iframe>"
    )
    assert expected_iframe in index_html


def test_colored_text(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Colored text from ``sphinxcontrib-text-styles`` becomes rich text.
    """
    rst_content = """
        This is :text-red:`red text` and :text-blue:`blue text` \
and :text-green:`green text`.
    """

    normal_text = text(text="This is ")
    red_text = text(text="red text", color=Color.RED)
    normal_text2 = text(text=" and ")
    blue_text = text(text="blue text", color=Color.BLUE)
    normal_text3 = text(text=" and ")
    green_text = text(text="green text", color=Color.GREEN)
    normal_text4 = text(text=".")

    combined_text = (
        normal_text
        + red_text
        + normal_text2
        + blue_text
        + normal_text3
        + green_text
        + normal_text4
    )

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinxcontrib_text_styles"),
    )


@pytest.mark.parametrize(
    argnames=("role", "expected_color"),
    argvalues=[
        ("text-red", Color.RED),
        ("text-blue", Color.BLUE),
        ("text-green", Color.GREEN),
        ("text-yellow", Color.YELLOW),
        ("text-orange", Color.ORANGE),
        ("text-purple", Color.PURPLE),
        ("text-pink", Color.PINK),
        ("text-brown", Color.BROWN),
        ("text-gray", Color.GRAY),
        ("bg-red", BGColor.RED),
        ("bg-blue", BGColor.BLUE),
        ("bg-green", BGColor.GREEN),
        ("bg-yellow", BGColor.YELLOW),
        ("bg-orange", BGColor.ORANGE),
        ("bg-purple", BGColor.PURPLE),
        ("bg-pink", BGColor.PINK),
        ("bg-brown", BGColor.BROWN),
        ("bg-gray", BGColor.GRAY),
    ],
)
def test_individual_colors(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    role: str,
    expected_color: Color | BGColor,
) -> None:
    """
    Each supported color is converted correctly.
    """
    rst_content = f"""
        This is :{role}:`{role} text`.
    """

    normal_text = text(text="This is ")
    colored_text = text(
        text=f"{role} text",
        # We ignore the type check here because Ultimate Notion has
        # a bad type hint: https://github.com/ultimate-notion/ultimate-notion/issues/140
        color=expected_color,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    )
    normal_text2 = text(text=".")

    combined_text = normal_text + colored_text + normal_text2

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinxcontrib_text_styles"),
    )


def test_text_styles_unsupported_color(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Unsupported colors from ``sphinxcontrib-text-styles`` emit warnings.
    """
    rst_content = """
        This is :text-cyan:`cyan text`.
    """

    expected_warning = (
        "Unsupported text style classes: text-cyan. "
        f"Text on line 1 in {tmp_path / 'src' / 'index.rst'} will be rendered "
        "without styling."
    )

    normal_text = text(text="This is ")
    cyan_text = text(text="cyan text")
    normal_text2 = text(text=".")

    combined_text = normal_text + cyan_text + normal_text2

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinxcontrib_text_styles"),
        expected_warnings=[expected_warning],
    )


def test_inline_node_without_classes(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Inline nodes without classes are handled as plain text.
    """
    # Using a custom role to create an inline node without classes
    conf_py_content = """
from docutils import nodes

def setup(app):
    app.add_role(
        'custom',
        lambda name, rawtext, text, lineno, inliner, options={}, content=[]:
            ([nodes.inline(rawtext, text)], [])
    )
    """

    rst_content = """
        This is :custom:`custom text`.
    """

    normal_text = text(text="This is ")
    custom_text = text(text="custom text")
    normal_text2 = text(text=".")

    combined_text = normal_text + custom_text + normal_text2

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        conf_py_content=conf_py_content,
    )


def test_text_styles_and_strike(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """There is no warning when using text styles and strike.

    This demonstrates a workaround for an issue where the extensions
    conflicted with each other.
    """
    rst_content = """
        This is :text-red:`red text` and :strike:`strikethrough text`.
    """

    normal_text = text(text="This is ")
    red_text = text(text="red text", color=Color.RED)
    normal_text2 = text(text=" and ")
    strikethrough_text = text(text="strikethrough text", strikethrough=True)
    normal_text3 = text(text=".")

    combined_text = (
        normal_text
        + red_text
        + normal_text2
        + strikethrough_text
        + normal_text3
    )

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=(
            "sphinx_notion",
            "sphinxcontrib_text_styles",
            "sphinxnotes.strike",
        ),
    )


@pytest.mark.parametrize(
    argnames=("role", "expected_text"),
    argvalues=[
        ("text-bold", text(text="text-bold text", bold=True)),
        ("text-italic", text(text="text-italic text", italic=True)),
        ("text-mono", text(text="text-mono text", code=True)),
        ("text-strike", text(text="text-strike text", strikethrough=True)),
        ("text-underline", text(text="text-underline text", underline=True)),
    ],
)
def test_additional_text_styles(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    role: str,
    expected_text: Text,
) -> None:
    """
    Additional text styles from the ``sphinxcontrib_text_styles`` extension are
    supported.
    """
    rst_content = f"""
        This is :{role}:`{role} text`.
    """

    normal_text1 = text(text="This is ")
    normal_text2 = text(text=".")

    combined_text = normal_text1 + expected_text + normal_text2

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinxcontrib_text_styles"),
    )


def test_flat_task_list(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Flat task lists become separate Notion ToDoItem blocks.
    """
    rst_content = """
        .. task-list::

           - [ ] Unchecked task item
           - [x] Checked task item
           - [ ] Another unchecked task with **bold text**
    """
    expected_objects: list[Block] = [
        UnoToDoItem(text=text(text="Unchecked task item"), checked=False),
        UnoToDoItem(text=text(text="Checked task item"), checked=True),
        UnoToDoItem(
            text=(
                text(text="Another unchecked task with ", bold=False)
                + text(text="bold text", bold=True)
            ),
            checked=False,
        ),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx_immaterial.task_lists"),
    )


def test_bullet_list_with_nested_content(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test that bullet lists can contain nested content like paragraphs and
    nested bullets.
    """
    rst_content = """
        * First bullet point

          This is a paragraph nested within a bullet list item.

          * Nested bullet point
          * Another nested bullet

        * Second bullet point

          Another nested paragraph.
    """

    first_bullet = UnoBulletedItem(text=text(text="First bullet point"))

    nested_paragraph = UnoParagraph(
        text=text(text="This is a paragraph nested within a bullet list item.")
    )
    first_bullet.append(blocks=[nested_paragraph])

    nested_bullet_1 = UnoBulletedItem(text=text(text="Nested bullet point"))
    nested_bullet_2 = UnoBulletedItem(text=text(text="Another nested bullet"))
    first_bullet.append(blocks=[nested_bullet_1])
    first_bullet.append(blocks=[nested_bullet_2])

    second_bullet = UnoBulletedItem(text=text(text="Second bullet point"))

    nested_paragraph_2 = UnoParagraph(
        text=text(text="Another nested paragraph.")
    )
    second_bullet.append(blocks=[nested_paragraph_2])

    expected_objects: list[Block] = [
        first_bullet,
        second_bullet,
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_task_list_with_nested_content(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Task lists with nested content should create ToDoItem blocks with nested
    children.
    """
    rst_content = """
        .. task-list::

           - [ ] Task with nested content

             This is a paragraph nested within the task item.

             * A bullet point nested within the task item.
    """

    # Create the main task item
    task_item = UnoToDoItem(
        text=text(text="Task with nested content"), checked=False
    )

    # Add nested paragraph
    nested_paragraph = UnoParagraph(
        text=text(text="This is a paragraph nested within the task item.")
    )
    task_item.append(blocks=[nested_paragraph])

    # Add nested bullet list
    nested_bullet = UnoBulletedItem(
        text=text(text="A bullet point nested within the task item.")
    )
    task_item.append(blocks=[nested_bullet])

    expected_objects: list[Block] = [task_item]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx_immaterial.task_lists"),
    )


def test_nested_task_list(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Nested task lists should create nested ToDoItem blocks.
    """
    rst_content = """
        .. task-list::

           1. [x] Task A
           2. [ ] Task B

              .. task-list::

                  * [x] Task B1
                  * [x] Task B2
                  * [ ] Task B3

              A rogue paragraph.

              - A list item without a checkbox.
              - [ ] Another bullet point.

           3. [ ] Task C
    """
    # Create Task B with nested children (including the rogue paragraph)
    task_b = UnoToDoItem(text=text(text="Task B"), checked=False)
    task_b.append(
        blocks=[UnoToDoItem(text=text(text="Task B1"), checked=True)]
    )
    task_b.append(
        blocks=[UnoToDoItem(text=text(text="Task B2"), checked=True)]
    )
    task_b.append(
        blocks=[UnoToDoItem(text=text(text="Task B3"), checked=False)]
    )
    # The rogue paragraph is nested within Task B
    # Note: The actual output has the text split across multiple rich text
    # segments
    rogue_paragraph = UnoParagraph(text=text(text="A rogue paragraph."))
    task_b.append(blocks=[rogue_paragraph])

    # Regular bullet list items should be nested within Task B as bullet items
    regular_bullet = UnoBulletedItem(
        text=text(text="A list item without a checkbox.")
    )
    task_b.append(blocks=[regular_bullet])

    # Another bullet item (has "[ ]" but should be treated as a bullet)
    another_bullet = UnoBulletedItem(
        text=text(text="[ ] Another bullet point.")
    )
    task_b.append(blocks=[another_bullet])

    expected_objects: list[Block] = [
        UnoToDoItem(text=text(text="Task A"), checked=True),
        task_b,
        UnoToDoItem(text=text(text="Task C"), checked=False),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx_immaterial.task_lists"),
    )


def test_task_list_quote(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    A quote can exist within a task list.
    """
    rst_content = """
    .. task-list::

        1. [x] Task A
        2. [ ] Task B

          foo
    """

    # The actual processing creates a flat structure where the quote
    # becomes a separate quote block
    expected_objects: list[Block] = [
        UnoToDoItem(text=text(text="Task A"), checked=True),
        UnoToDoItem(text=text(text="Task B"), checked=False),
        UnoQuote(text=text(text="foo")),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx_immaterial.task_lists"),
    )


def test_inline_single_backticks(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Reproduces a bug where we got confused by mismatching blocks.
    """
    rst_content = """
        A `B`
    """
    expected_objects: list[Block] = [
        UnoParagraph(text=text(text="A ") + text(text="B", italic=True)),
    ]
    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_kbd_role(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The ``:kbd:`` role creates keyboard input formatting.

    The ``:kbd:`` role splits keyboard shortcuts into separate segments,
    where each key is formatted as code but the + separator is not.
    """
    rst_content = """
        Press :kbd:`Ctrl+C` to copy and :kbd:`Ctrl+V` to paste.
    """

    normal_text1 = text(text="Press ")
    kbd_text1 = text(text="Ctrl", code=True)
    plus_text1 = text(text="+", code=False)
    kbd_text2 = text(text="C", code=True)
    normal_text2 = text(text=" to copy and ")
    kbd_text3 = text(text="Ctrl", code=True)
    plus_text2 = text(text="+", code=False)
    kbd_text4 = text(text="V", code=True)
    normal_text3 = text(text=" to paste.")

    combined_text = (
        normal_text1
        + kbd_text1
        + plus_text1
        + kbd_text2
        + normal_text2
        + kbd_text3
        + plus_text2
        + kbd_text4
        + normal_text3
    )

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_file_role(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The ``:file:`` role creates file path formatting.

    File paths should be rendered as inline code.
    """
    rst_content = """
        Edit the :file:`config.py` file.
    """

    normal_text1 = text(text="Edit the ")
    file_text = text(text="config.py", code=True)
    normal_text2 = text(text=" file.")

    combined_text = normal_text1 + file_text + normal_text2

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_unsupported_node_types_in_rich_text(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Unsupported node types in rich text processing raise ValueError.
    """
    rst_content = """
        This is a test with :footnote:`footnote node`.
    """

    conf_py_content = """
from docutils import nodes

def setup(app):
    def footnote_role(
        name, rawtext, text, lineno, inliner, options={}, content=[]
    ):  # noqa: PLR0913
        node = nodes.footnote_reference(rawtext, text)
        return [node], []

    app.add_role('footnote', footnote_role)
    """
    expected_message = (
        r"^Unsupported node type within text: footnote_reference on line 1 in "
        rf"{re.escape(pattern=str(object=tmp_path / 'src' / 'index.rst'))}\.$"
    )
    with pytest.raises(expected_exception=ValueError, match=expected_message):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
            conf_py_content=conf_py_content,
        )


@pytest.mark.parametrize(
    argnames=("rst_content", "node_name", "line_number_available"),
    argvalues=[
        (".. raw:: html\n\n   <hr width=50 size=10>", "raw", True),
        (
            ".. sidebar:: title\n\n   content",
            "sidebar",
            False,
        ),
    ],
)
def test_unsupported_node_types_in_process_node_to_blocks(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    rst_content: str,
    node_name: str,
    line_number_available: bool,
) -> None:
    """
    Unsupported node types in _process_node_to_blocks raise
    ``NotImplementedError``.
    """
    index_rst = tmp_path / "src" / "index.rst"
    # Some nodes do not have a line number available.
    if line_number_available:
        expected_message = (
            rf"^Unsupported node type: {node_name} on line "
            rf"1 in "
            rf"{re.escape(pattern=str(object=index_rst))}.$"
        )
    else:
        expected_message = rf"^Unsupported node type: {node_name}.$"
    with pytest.raises(
        expected_exception=NotImplementedError,
        match=expected_message,
    ):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
        )


def test_inline_equation(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Inline equations become Notion math rich text.
    """
    rst_content = """
        This is an inline equation :math:`E = mc^2` in a paragraph.
    """

    normal_text1 = text(text="This is an inline equation ")
    equation_text = math(expression="E = mc^2")
    normal_text2 = text(text=" in a paragraph.")

    combined_text = normal_text1 + equation_text + normal_text2

    expected_paragraph = UnoParagraph(text=combined_text)

    expected_objects: list[Block] = [expected_paragraph]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx.ext.mathjax"),
    )


def test_block_equation(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Block equations become Notion Equation blocks.
    """
    rst_content = """
        .. math::

           E = mc^2
    """

    expected_objects: list[Block] = [
        UnoEquation(latex="E = mc^2"),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx.ext.mathjax"),
    )


def test_rest_example_block(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Rest example blocks become Notion callout blocks with nested code and
    description.
    """
    rst_content = """
        .. rest-example::

           .. code-block:: python

              def hello_world():
                  print("Hello, World!")

           Rendered output shows what the code does.
    """

    code_callout = UnoCallout(
        text=text(text="Code"),
    )
    code_callout.append(
        blocks=[
            UnoCode(
                text=text(
                    text=textwrap.dedent(
                        text="""\
                        .. code-block:: python

                           def hello_world():
                               print("Hello, World!")

                        Rendered output shows what the code does."""
                    )
                ),
                language="plain text",
            ),
        ]
    )

    output_callout = UnoCallout(
        text=text(text="Output"),
    )
    output_callout.append(
        blocks=[
            UnoCode(
                text=text(
                    text=textwrap.dedent(
                        text="""\
                        def hello_world():
                            print("Hello, World!")""",
                    )
                ),
                language="python",
            ),
            UnoParagraph(
                text=text(text="Rendered output shows what the code does.")
            ),
        ]
    )

    main_callout = UnoCallout(text=text(text="Example"))
    main_callout.append(blocks=[code_callout, output_callout])

    expected_objects: list[Block] = [main_callout]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx_toolbox.rest_example"),
    )


def test_embed_block(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Blocks using the ``iframe`` directive become Notion Embed blocks.
    """
    rst_content = """
        .. iframe:: https://example.com/embed
           :width: 600
           :height: 400
    """

    expected_objects: list[Block] = [UnoEmbed(url="https://example.com/embed")]

    # Create the _static directory that ``sphinx-iframes`` expects
    static_dir = tmp_path / "build" / "notion" / "_static"
    static_dir.mkdir(parents=True, exist_ok=True)

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinx_notion", "sphinx_iframes"),
    )


def test_embed_and_video(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``sphinx-iframes`` and ``sphinxcontrib.video`` can be used together in
    this with ``sphinx-notionbuilder``.

    We check this because there was a conflict between the two
    extensions. See
    https://github.com/TeachBooks/sphinx-iframes/issues/8.
    """
    rst_content = """
        .. iframe:: https://example.com/embed

        .. video:: https://example.com/video.mp4
    """

    expected_objects: list[Block] = [
        UnoEmbed(url="https://example.com/embed"),
        UnoVideo(file=ExternalFile(url="https://example.com/video.mp4")),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=("sphinxcontrib.video", "sphinx_iframes", "sphinx_notion"),
    )


def test_line_block(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Line blocks (created with pipe character) become empty Notion paragraph
    blocks.
    """
    rst_content = """
        | This is a line block
        | with multiple lines
        | preserved exactly as written
    """

    expected_objects: list[Block] = [
        UnoParagraph(
            text=text(text="This is a line block")
            + text(text="\n")
            + text(text="with multiple lines")
            + text(text="\n")
            + text(text="preserved exactly as written")
            + text(text="\n")
        ),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )


def test_transition_divider(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Transitions (horizontal rules) become Notion Divider blocks.
    """
    rst_content = """
        First paragraph.

        ----

        Second paragraph.
    """

    expected_objects: list[Block] = [
        UnoParagraph(text=text(text="First paragraph.")),
        UnoDivider(),
        UnoParagraph(text=text(text="Second paragraph.")),
    ]

    _assert_rst_converts_to_notion_objects(
        rst_content=rst_content,
        expected_objects=expected_objects,
        make_app=make_app,
        tmp_path=tmp_path,
    )
