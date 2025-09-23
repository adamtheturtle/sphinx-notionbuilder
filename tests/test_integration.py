"""
Integration tests for the Sphinx Notion Builder functionality.
"""

import base64
import json
import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from beartype import beartype
from sphinx.testing.util import SphinxTestApp
from ultimate_notion import Emoji
from ultimate_notion.blocks import Block, ChildrenMixin
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
from ultimate_notion.blocks import (
    ToggleItem as UnoToggleItem,
)
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.file import ExternalFile
from ultimate_notion.obj_api.enums import BGColor, CodeLang
from ultimate_notion.rich_text import text


@beartype
def _details_from_block(
    *,
    block: Block,
) -> dict[str, Any]:
    """
    Create a serialized block details from a Block.
    """
    serialized_obj = block.obj_ref.serialize_for_api()
    if isinstance(block, ChildrenMixin) and block.children:
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
) -> None:
    """
    ReStructuredText content converts to expected Notion objects via Sphinx
    build process.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir(exist_ok=True)

    (srcdir / "conf.py").write_text(data=conf_py_content)

    cleaned_content = textwrap.dedent(text=rst_content).strip()
    (srcdir / "index.rst").write_text(data=cleaned_content)

    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
        confoverrides={"extensions": list(extensions)},
    )
    app.build()

    output_file = app.outdir / "index.json"
    with output_file.open(encoding="utf-8") as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    expected_json: list[dict[str, Any]] = [
        _details_from_block(block=expected_object)
        for expected_object in expected_objects
    ]

    assert generated_json == expected_json


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
        extensions=("sphinx_notion", "sphinxcontrib.video"),
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
        extensions=("sphinx_notion", "sphinxcontrib.video"),
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
        extensions=("sphinx_notion", "sphinxcontrib.video"),
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


def test_bullet_list_item_invalid_nested_child_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Bullet list items with invalid nested children raise a clear error message.
    """
    rst_content = """
        * First bullet point

          Some paragraph that should not be here

          * Nested bullet
    """

    index_rst = tmp_path / "src" / "index.rst"
    expected_message = (
        r"^The only thing Notion supports within a bullet list is a "
        r"bullet list. Given paragraph on line 3 "
        rf"in {re.escape(pattern=str(object=index_rst))}$"
    )
    with pytest.raises(expected_exception=ValueError, match=expected_message):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
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
    List table with header-rows option other than 0 or 1 raises ValueError.
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

    expected_message = (
        r"^Tables with multiple header rows are not supported. "
        r"First header row is on line 4 in "
        rf"{re.escape(pattern=str(object=tmp_path / 'src' / 'index.rst'))}, "
        r"last header row is on line 6"
    )
    with pytest.raises(expected_exception=ValueError, match=expected_message):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
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
    List table with :stub-columns: 2 raises ValueError.
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

    expected_message = (
        r"^Tables with more than 1 stub column are not supported. "
        r"Found 2 stub columns.$"
    )
    with pytest.raises(expected_exception=ValueError, match=expected_message):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
        )


def test_list_table_with_title_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    List table with title raises ValueError since Notion tables do not have
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

    expected_message = (
        r"^Table has a title 'My Table Title' on line 1 in "
        rf"{re.escape(pattern=str(object=tmp_path / 'src' / 'index.rst'))}, "
        r"but Notion tables do not "
        r"have titles.$"
    )
    with pytest.raises(expected_exception=ValueError, match=expected_message):
        _assert_rst_converts_to_notion_objects(
            rst_content=rst_content,
            expected_objects=[],
            make_app=make_app,
            tmp_path=tmp_path,
        )
