"""
Sphinx Notion Builder.
"""

import json
import logging
from dataclasses import dataclass
from functools import singledispatch
from pathlib import Path
from typing import Any

import sphinxnotes.strike
from atsphinx.audioplayer.nodes import (  # pyright: ignore[reportMissingTypeStubs]
    audio as audio_node,
)
from beartype import beartype
from docutils import nodes
from docutils.nodes import NodeVisitor
from sphinx.application import Sphinx
from sphinx.builders.text import TextBuilder
from sphinx.util import docutils as sphinx_docutils
from sphinx.util import logging as sphinx_logging
from sphinx.util.typing import ExtensionMetadata
from sphinx_immaterial.task_lists import checkbox_label
from sphinx_simplepdf.directives.pdfinclude import (  # pyright: ignore[reportMissingTypeStubs]
    PdfIncludeDirective,
)
from sphinx_toolbox.collapse import CollapseNode
from sphinxcontrib.video import (  # pyright: ignore[reportMissingTypeStubs]
    video_node,
)
from sphinxnotes.strike import strike_node
from ultimate_notion import Emoji
from ultimate_notion.blocks import PDF as UnoPDF  # noqa: N811
from ultimate_notion.blocks import Audio as UnoAudio
from ultimate_notion.blocks import Block, ParentBlock
from ultimate_notion.blocks import BulletedItem as UnoBulletedItem
from ultimate_notion.blocks import Callout as UnoCallout
from ultimate_notion.blocks import Code as UnoCode
from ultimate_notion.blocks import Heading as UnoHeading
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
from ultimate_notion.rich_text import Text, text

_LOGGER = sphinx_logging.getLogger(name=__name__)


@beartype
def _color_from_node(*, node: nodes.inline) -> Color | None:
    """Extract Notion color from CSS classes.

    ``sphinxcontrib-text-styles`` creates classes like 'text-red', 'text-
    blue', etc.
    """
    classes = node.attributes.get("classes", [])
    color_mapping: dict[str, Color] = {
        "text-red": Color.RED,
        "text-blue": Color.BLUE,
        "text-green": Color.GREEN,
        "text-yellow": Color.YELLOW,
        "text-orange": Color.ORANGE,
        "text-purple": Color.PURPLE,
        "text-pink": Color.PINK,
        "text-brown": Color.BROWN,
        "text-gray": Color.GRAY,
        "text-grey": Color.GRAY,
    }

    for css_class in classes:
        if css_class in color_mapping:
            return color_mapping[css_class]

        # This warning being here assumes that only color classes,
        # and only classes from ``sphinxcontrib-text-styles``, are used.
        _LOGGER.warning(
            "Unsupported text style classes: %s. "
            "Text will be rendered without styling.",
            css_class,
        )

    return None


@beartype
def _serialize_block_with_children(
    *,
    block: Block,
) -> dict[str, Any]:
    """
    Convert a block to a JSON-serializable format which includes its children.
    """
    serialized_obj = block.obj_ref.serialize_for_api()
    if isinstance(block, ParentBlock) and block.children:
        serialized_obj[block.obj_ref.type]["children"] = [
            _serialize_block_with_children(block=child)
            for child in block.children
        ]
    return serialized_obj


@beartype
class _PdfNode(nodes.raw):  # pylint: disable=too-many-ancestors
    """
    Custom PDF node for Notion PDF blocks.
    """


@beartype
class _NotionPdfIncludeDirective(PdfIncludeDirective):
    """
    PDF include directive that creates Notion PDF blocks.
    """

    def run(self) -> list[nodes.raw]:
        """
        Create a Notion PDF block.
        """
        (pdf_file,) = self.arguments
        node = _PdfNode()
        node.attributes["uri"] = pdf_file
        return [node]


@dataclass
class _TableStructure:
    """
    Structure information extracted from a table node.
    """

    header_rows: list[nodes.row]
    body_rows: list[nodes.row]
    num_stub_columns: int


@beartype
def _create_rich_text_from_children(*, node: nodes.Element) -> Text:
    """Create Notion rich text from ``docutils`` node children.

    This uses ``ultimate-notion``'s rich text capabilities to
    avoid some size limits.

    See: https://developers.notion.com/reference/request-limits#size-limits.
    """
    rich_text = Text.from_plain_text(text="")

    for child in node.children:
        if isinstance(child, nodes.reference):
            link_url = child.attributes["refuri"]
            link_text = child.attributes.get("name", link_url)

            new_text = text(
                text=link_text,
                href=link_url,
                bold=False,
                italic=False,
                code=False,
            )
        elif isinstance(child, nodes.target):
            continue
        elif isinstance(child, nodes.inline):
            new_text = text(
                text=child.astext(),
                bold=isinstance(child, nodes.strong),
                italic=isinstance(child, nodes.emphasis),
                code=isinstance(child, nodes.literal),
                strikethrough=isinstance(child, strike_node),
                color=_color_from_node(node=child),
            )
        else:
            new_text = text(
                text=child.astext(),
                bold=isinstance(child, nodes.strong),
                italic=isinstance(child, nodes.emphasis),
                code=isinstance(child, nodes.literal),
                strikethrough=isinstance(child, strike_node),
            )
        rich_text += new_text

    return rich_text


@beartype
def _extract_table_structure(
    *,
    node: nodes.table,
) -> _TableStructure:
    """
    Return table structure information for a table node.
    """
    header_rows: list[nodes.row] = []
    body_rows: list[nodes.row] = []
    stub_columns = 0

    # In Notion, all rows must have the same number of columns.
    # Therefore there is only one ``tgroup``.
    tgroups = [
        child for child in node.children if isinstance(child, nodes.tgroup)
    ]
    (tgroup,) = tgroups

    for tgroup_child in tgroup.children:
        if isinstance(tgroup_child, nodes.colspec):
            if tgroup_child.attributes.get("stub"):
                stub_columns += 1
        elif isinstance(tgroup_child, nodes.thead):
            for row in tgroup_child.children:
                assert isinstance(row, nodes.row)
                header_rows.append(row)
        else:
            assert isinstance(tgroup_child, nodes.tbody)
            for row in tgroup_child.children:
                assert isinstance(row, nodes.row)
                body_rows.append(row)

    return _TableStructure(
        header_rows=header_rows,
        body_rows=body_rows,
        num_stub_columns=stub_columns,
    )


@beartype
def _cell_source_node(*, entry: nodes.Node) -> nodes.paragraph:
    """Return the paragraph child of an entry if present, else the entry.

    This isolates the small branch used when converting a table cell so
    the main table function becomes simpler.

    Notion table cells can only contain paragraph content, so we
    validate that all children are paragraphs.
    """
    paragraph_children = [
        c for c in entry.children if isinstance(c, nodes.paragraph)
    ]
    if len(paragraph_children) == 1:
        return paragraph_children[0]

    # Check for non-paragraph content and raise an error
    non_paragraph_children = [
        c for c in entry.children if not isinstance(c, nodes.paragraph)
    ]
    if non_paragraph_children:
        first_child = non_paragraph_children[0]
        msg = (
            f"Notion table cells can only contain paragraph content. "
            f"Found non-paragraph node: {type(first_child).__name__} on line "
            f"{first_child.line} in {first_child.source}."
        )
        raise ValueError(msg)

    # If there are multiple paragraph children, create a combined node
    # that preserves all content and rich text formatting.
    combined = nodes.paragraph()

    for i, child in enumerate(iterable=entry.children):
        if i > 0:
            # Add double newline between paragraphs to maintain separation
            combined += nodes.Text(data="\n\n")

        # Add the paragraph's children directly to preserve formatting
        for grandchild in child.children:
            combined += grandchild

    return combined


@beartype
def _map_pygments_to_notion_language(*, pygments_lang: str) -> CodeLang:
    """
    Map ``Pygments`` language names to Notion CodeLang ``enum`` values.
    """
    language_mapping: dict[str, CodeLang] = {
        "abap": CodeLang.ABAP,
        "arduino": CodeLang.ARDUINO,
        "bash": CodeLang.BASH,
        "basic": CodeLang.BASIC,
        "c": CodeLang.C,
        "clojure": CodeLang.CLOJURE,
        "coffeescript": CodeLang.COFFEESCRIPT,
        "console": CodeLang.SHELL,
        "cpp": CodeLang.CPP,
        "c++": CodeLang.CPP,
        "csharp": CodeLang.CSHARP,
        "c#": CodeLang.CSHARP,
        "css": CodeLang.CSS,
        "dart": CodeLang.DART,
        "default": CodeLang.PLAIN_TEXT,
        "diff": CodeLang.DIFF,
        "docker": CodeLang.DOCKER,
        "dockerfile": CodeLang.DOCKER,
        "elixir": CodeLang.ELIXIR,
        "elm": CodeLang.ELM,
        "erlang": CodeLang.ERLANG,
        "flow": CodeLang.FLOW,
        "fortran": CodeLang.FORTRAN,
        "fsharp": CodeLang.FSHARP,
        "f#": CodeLang.FSHARP,
        "gherkin": CodeLang.GHERKIN,
        "glsl": CodeLang.GLSL,
        "go": CodeLang.GO,
        "graphql": CodeLang.GRAPHQL,
        "groovy": CodeLang.GROOVY,
        "haskell": CodeLang.HASKELL,
        # This is not a perfect match, but at least JSON within the
        # HTTP definition will be highlighted.
        "http": CodeLang.JSON,
        "html": CodeLang.HTML,
        "java": CodeLang.JAVA,
        "javascript": CodeLang.JAVASCRIPT,
        "js": CodeLang.JAVASCRIPT,
        "json": CodeLang.JSON,
        "julia": CodeLang.JULIA,
        "kotlin": CodeLang.KOTLIN,
        "latex": CodeLang.LATEX,
        "tex": CodeLang.LATEX,
        "less": CodeLang.LESS,
        "lisp": CodeLang.LISP,
        "livescript": CodeLang.LIVESCRIPT,
        "lua": CodeLang.LUA,
        "makefile": CodeLang.MAKEFILE,
        "make": CodeLang.MAKEFILE,
        "markdown": CodeLang.MARKDOWN,
        "md": CodeLang.MARKDOWN,
        "markup": CodeLang.MARKUP,
        "matlab": CodeLang.MATLAB,
        "mermaid": CodeLang.MERMAID,
        "nix": CodeLang.NIX,
        "objective-c": CodeLang.OBJECTIVE_C,
        "objc": CodeLang.OBJECTIVE_C,
        "ocaml": CodeLang.OCAML,
        "pascal": CodeLang.PASCAL,
        "perl": CodeLang.PERL,
        "php": CodeLang.PHP,
        "powershell": CodeLang.POWERSHELL,
        "ps1": CodeLang.POWERSHELL,
        "prolog": CodeLang.PROLOG,
        "protobuf": CodeLang.PROTOBUF,
        "python": CodeLang.PYTHON,
        "py": CodeLang.PYTHON,
        "r": CodeLang.R,
        "reason": CodeLang.REASON,
        "ruby": CodeLang.RUBY,
        "rb": CodeLang.RUBY,
        "rust": CodeLang.RUST,
        "rs": CodeLang.RUST,
        "sass": CodeLang.SASS,
        "scala": CodeLang.SCALA,
        "scheme": CodeLang.SCHEME,
        "scss": CodeLang.SCSS,
        "shell": CodeLang.SHELL,
        "sh": CodeLang.SHELL,
        "sql": CodeLang.SQL,
        "swift": CodeLang.SWIFT,
        "text": CodeLang.PLAIN_TEXT,
        "toml": CodeLang.TOML,
        "typescript": CodeLang.TYPESCRIPT,
        "ts": CodeLang.TYPESCRIPT,
        # This is not a perfect match, but it's the best we can do.
        "tsx": CodeLang.TYPESCRIPT,
        "udiff": CodeLang.DIFF,
        "vb.net": CodeLang.VB_NET,
        "vbnet": CodeLang.VB_NET,
        "verilog": CodeLang.VERILOG,
        "vhdl": CodeLang.VHDL,
        "visual basic": CodeLang.VISUAL_BASIC,
        "vb": CodeLang.VISUAL_BASIC,
        "webassembly": CodeLang.WEBASSEMBLY,
        "wasm": CodeLang.WEBASSEMBLY,
        "xml": CodeLang.XML,
        "yaml": CodeLang.YAML,
        "yml": CodeLang.YAML,
    }

    return language_mapping[pygments_lang.lower()]


@singledispatch
@beartype
def _process_node_to_blocks(
    node: nodes.Element,
    *,
    section_level: int,
) -> list[Block]:  # pragma: no cover
    """
    Required function for ``singledispatch``.
    """
    del section_level
    raise NotImplementedError(node)


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.table,
    *,
    section_level: int,
) -> list[Block]:
    """Process rST table nodes by creating Notion Table blocks.

    This implementation delegates small branches to helpers which keeps
    the function body linear and easier to reason about.
    """
    del section_level

    for child in node.children:
        if isinstance(child, nodes.title):
            table_no_titles_msg = (
                f"Table has a title '{child.astext()}' on line "
                f"{child.line} in {child.source}, but Notion tables "
                "do not have titles."
            )
            _LOGGER.warning(msg=table_no_titles_msg)

    table_structure = _extract_table_structure(node=node)

    if len(table_structure.header_rows) > 1:
        first_header_row = table_structure.header_rows[0]
        first_header_row_entry = first_header_row.children[0]
        first_header_row_paragraph = first_header_row_entry.children[0]
        first_header_row_line = first_header_row_paragraph.line
        last_header_row = table_structure.header_rows[-1]
        last_header_row_entry = last_header_row.children[0]
        last_header_row_paragraph = last_header_row_entry.children[0]
        last_header_row_line = last_header_row_paragraph.line
        table_multiple_header_rows_msg = (
            "Tables with multiple header rows are not supported. "
            f"First header row is on line {first_header_row_line} in "
            f"{first_header_row_paragraph.source}, last header row is on "
            f"line {last_header_row_line}"
        )
        _LOGGER.warning(msg=table_multiple_header_rows_msg)

    if table_structure.num_stub_columns > 1:
        table_more_than_one_stub_column_msg = (
            f"Tables with more than 1 stub column are not supported. "
            f"Found {table_structure.num_stub_columns} stub columns."
        )
        _LOGGER.warning(msg=table_more_than_one_stub_column_msg)

    rows = [*table_structure.header_rows, *table_structure.body_rows]
    table = UnoTable(
        n_rows=len(rows),
        # In Notion, all rows must have the same number of columns.
        n_cols=len(rows[0]),
        header_row=bool(table_structure.header_rows),
        header_col=bool(table_structure.num_stub_columns),
    )

    for row_index, row in enumerate(iterable=rows):
        for column_index, entry in enumerate(iterable=row.children):
            source = _cell_source_node(entry=entry)
            table[row_index, column_index] = _create_rich_text_from_children(
                node=source
            )

    return [table]


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.paragraph,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process paragraph nodes by creating Notion Paragraph blocks.
    """
    del section_level
    rich_text = _create_rich_text_from_children(node=node)
    return [UnoParagraph(text=rich_text)]


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.block_quote,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process block quote nodes by creating Notion Quote blocks.
    """
    del section_level
    rich_text = _create_rich_text_from_children(node=node)
    return [UnoQuote(text=rich_text)]


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.literal_block,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process literal block nodes by creating Notion Code blocks.
    """
    del section_level
    code_text = _create_rich_text_from_children(node=node)
    pygments_lang = node.get(key="language", failobj="")
    language = _map_pygments_to_notion_language(
        pygments_lang=pygments_lang,
    )
    return [UnoCode(text=code_text, language=language)]


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.bullet_list,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process bullet list nodes by creating Notion BulletedItem blocks.
    """
    result: list[Block] = []
    for list_item in node.children:
        assert isinstance(list_item, nodes.list_item)
        first_child = list_item.children[0]
        if isinstance(first_child, nodes.paragraph):
            paragraph = first_child
            rich_text = _create_rich_text_from_children(node=paragraph)
            bulleted_item_block = UnoBulletedItem(text=rich_text)

            for child in list_item.children[1:]:
                child_blocks = _process_node_to_blocks(
                    child,
                    section_level=section_level,
                )
                bulleted_item_block.append(blocks=child_blocks)
            result.append(bulleted_item_block)
        else:
            assert isinstance(first_child, checkbox_label)
            label_text_node = list_item.children[1]
            # Get the checked state from the checkbox_label node
            checked = first_child.attributes.get("checked", False)
            assert isinstance(label_text_node, nodes.paragraph)
            rich_text = _create_rich_text_from_children(
                node=label_text_node,
            )
            todo_item_block = UnoToDoItem(text=rich_text, checked=checked)

            for child in list_item.children[2:]:
                child_blocks = _process_node_to_blocks(
                    child,
                    section_level=section_level,
                )
                todo_item_block.append(blocks=child_blocks)
            result.append(todo_item_block)
    return result


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.enumerated_list,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process enumerated list nodes by creating Notion NumberedItem or ToDoItem
    blocks.
    """
    result: list[Block] = []
    for list_item in node.children:
        assert isinstance(list_item, nodes.list_item)
        first_child = list_item.children[0]
        if isinstance(first_child, nodes.paragraph):
            paragraph = first_child
            rich_text = _create_rich_text_from_children(node=paragraph)
            block = UnoNumberedItem(text=rich_text)

            for child in list_item.children[1:]:
                child_blocks = _process_node_to_blocks(
                    child,
                    section_level=section_level,
                )
                block.append(blocks=child_blocks)
            result.append(block)
        else:
            assert isinstance(first_child, checkbox_label)
            label_text_node = list_item.children[1]
            # Get the checked state from the checkbox_label node
            checked = first_child.attributes.get("checked", False)
            assert isinstance(label_text_node, nodes.paragraph)
            rich_text = _create_rich_text_from_children(
                node=label_text_node,
            )
            todo_item_block = UnoToDoItem(text=rich_text, checked=checked)

            for child in list_item.children[2:]:
                child_blocks = _process_node_to_blocks(
                    child,
                    section_level=section_level,
                )
                todo_item_block.append(blocks=child_blocks)
            result.append(todo_item_block)
    return result


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.topic,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process topic nodes, specifically for table of contents.
    """
    del section_level  # Not used for topics
    # Later, we can support `.. topic::` directives, likely as
    # a callout with no icon.
    assert "contents" in node["classes"]
    return [UnoTableOfContents()]


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.compound,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process Sphinx ``toctree`` nodes.
    """
    del node
    del section_level
    # There are no specific Notion blocks for ``toctree`` nodes.
    # We need to support ``toctree`` in ``index.rst``.
    # Just ignore it.
    return []


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.title,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process title nodes by creating appropriate Notion heading blocks.
    """
    rich_text = _create_rich_text_from_children(node=node)

    max_heading_level = 3
    if section_level > max_heading_level:
        error_msg = (
            f"Notion only supports heading levels 1-{max_heading_level}, "
            f"but found heading level {section_level} on line {node.line} "
            f"in {node.source}."
        )
        raise ValueError(error_msg)

    heading_levels: dict[int, type[UnoHeading[Any]]] = {
        1: UnoHeading1,
        2: UnoHeading2,
        3: UnoHeading3,
    }
    heading_cls = heading_levels[section_level]
    return [heading_cls(text=rich_text)]


@beartype
def _create_admonition_callout(
    *,
    node: nodes.Element,
    emoji: str,
    background_color: BGColor,
) -> list[Block]:
    """Create a Notion Callout block for admonition nodes.

    The first child (typically a paragraph) becomes the callout text,
    and any remaining children become nested blocks within the callout.
    """
    # Use the first child as the callout text
    first_child = node.children[0]
    if isinstance(first_child, nodes.paragraph):
        rich_text = _create_rich_text_from_children(node=first_child)
        # Process remaining children as nested blocks
        children_to_process = node.children[1:]
    else:
        # If first child is not a paragraph, use empty text
        rich_text = Text.from_plain_text(text="")
        # Process all children as nested blocks (including the first)
        children_to_process = node.children

    block = UnoCallout(
        text=rich_text,
        icon=Emoji(emoji=emoji),
        color=background_color,
    )

    for child in children_to_process:
        block.append(
            blocks=_process_node_to_blocks(
                child,
                section_level=1,
            )
        )
    return [block]


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.note,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process note admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="📝",
        background_color=BGColor.BLUE,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.warning,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process warning admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="⚠️",
        background_color=BGColor.YELLOW,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.tip,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process tip admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="💡",
        background_color=BGColor.GREEN,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.attention,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process attention admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="👀",
        background_color=BGColor.YELLOW,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.caution,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process caution admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="⚠️",
        background_color=BGColor.YELLOW,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.danger,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process danger admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="🚨",
        background_color=BGColor.RED,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.error,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process error admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="❌",
        background_color=BGColor.RED,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.hint,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process hint admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="💡",
        background_color=BGColor.GREEN,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.important,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process important admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(
        node=node,
        emoji="❗",
        background_color=BGColor.RED,
    )


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.admonition,
    *,
    section_level: int,
) -> list[Block]:
    """Process generic admonition nodes by creating Notion Callout blocks.

    Generic admonitions have a title as the first child, followed by
    content. The title becomes the callout text, and all content becomes
    nested blocks.
    """
    del section_level

    # Extract the title from the first child (admonitions always have title
    # as first child)
    title_node = node.children[0]
    assert isinstance(title_node, nodes.title)
    title_text = title_node.astext()
    # All remaining children become nested blocks
    content_children = node.children[1:]

    block = UnoCallout(
        text=text(text=title_text),
        icon=Emoji(emoji="💬"),
        color=BGColor.GRAY,
    )

    for child in content_children:
        block.append(
            blocks=_process_node_to_blocks(
                child,
                section_level=1,
            )
        )

    return [block]


@beartype
@_process_node_to_blocks.register
def _(
    node: CollapseNode,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process collapse nodes by creating Notion ToggleItem blocks.
    """
    del section_level

    title_text = node.attributes["label"]
    toggle_block = UnoToggleItem(text=text(text=title_text))

    for child in node.children:
        toggle_block.append(
            blocks=_process_node_to_blocks(
                child,
                section_level=1,
            )
        )

    return [toggle_block]


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.image,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process image nodes by creating Notion Image blocks.
    """
    del section_level

    image_url = node.attributes["uri"]
    assert isinstance(image_url, str)

    assert node.document is not None
    if "://" not in image_url:
        abs_path = Path(node.document.settings.env.srcdir) / image_url
        image_url = abs_path.as_uri()

    return [UnoImage(file=ExternalFile(url=image_url), caption=None)]


@beartype
@_process_node_to_blocks.register
def _(
    node: video_node,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process video nodes by creating Notion Video blocks.
    """
    del section_level

    sources: list[tuple[str, str, bool]] = node.attributes["sources"]
    assert isinstance(sources, list)
    primary_source = sources[0]
    video_location, _, is_remote = primary_source

    if is_remote:
        video_url = video_location
    else:
        assert node.document is not None
        abs_path = Path(node.document.settings.env.srcdir) / video_location
        video_url = abs_path.as_uri()

    caption_text = node.attributes["caption"]
    caption = text(text=caption_text) if caption_text else None

    return [
        UnoVideo(
            file=ExternalFile(url=video_url),
            caption=caption,
        )
    ]


@beartype
@_process_node_to_blocks.register
def _(
    node: audio_node,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process audio nodes by creating Notion Audio blocks.
    """
    del section_level

    audio_url = node.attributes["uri"]
    assert isinstance(audio_url, str)

    assert node.document is not None
    if "://" not in audio_url:
        abs_path = Path(node.document.settings.env.srcdir) / audio_url
        audio_url = abs_path.as_uri()

    return [UnoAudio(file=ExternalFile(url=audio_url))]


@beartype
@_process_node_to_blocks.register
def _(
    node: _PdfNode,
    *,
    section_level: int,
) -> list[Block]:
    """Process PDF nodes by creating Notion PDF blocks.

    This handles nodes created by our custom NotionPdfIncludeDirective.
    """
    del section_level

    pdf_url = node.attributes["uri"]

    if "://" not in pdf_url:
        assert node.document is not None
        abs_path = Path(node.document.settings.env.srcdir) / pdf_url
        pdf_url = abs_path.as_uri()

    return [UnoPDF(file=ExternalFile(url=pdf_url))]


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.container,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process container nodes, especially for ``literalinclude`` with captions.
    """
    num_children_for_captioned_literalinclude = 2
    if (
        len(node.children) == num_children_for_captioned_literalinclude
        and isinstance(node.children[0], nodes.caption)
        and isinstance(node.children[1], nodes.literal_block)
    ):
        caption_node, literal_node = node.children
        assert isinstance(caption_node, nodes.caption)
        assert isinstance(literal_node, nodes.literal_block)
        caption_rich_text = _create_rich_text_from_children(node=caption_node)

        code_text = _create_rich_text_from_children(node=literal_node)
        pygments_lang = literal_node.get(key="language", failobj="")
        language = _map_pygments_to_notion_language(
            pygments_lang=pygments_lang,
        )

        return [
            UnoCode(
                text=code_text,
                language=language,
                caption=caption_rich_text,
            )
        ]

    blocks: list[Block] = []
    for child in node.children:
        child_blocks = _process_node_to_blocks(
            child, section_level=section_level
        )
        blocks.extend(child_blocks)
    return blocks


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.comment,
    *,
    section_level: int,
) -> list[Block]:
    """Process comment nodes by ignoring them completely.

    Comments in reStructuredText should not appear in the final output.
    """
    del node
    del section_level
    return []


@beartype
@_process_node_to_blocks.register
def _(
    node: nodes.document,
    *,
    section_level: int,
) -> list[Block]:
    """
    Process document nodes by ignoring them completely.
    """
    del node
    del section_level
    return []


@beartype
class NotionTranslator(NodeVisitor):
    """
    Translate ``docutils`` nodes to Notion JSON.
    """

    def __init__(self, document: nodes.document, builder: TextBuilder) -> None:
        """
        Initialize the translator with storage for blocks.
        """
        del builder
        super().__init__(document=document)
        self._blocks: list[Block] = []
        self.body: str
        self._section_level = 0

    def dispatch_visit(self, node: nodes.Node) -> None:
        """
        Handle nodes by creating appropriate Notion heading blocks.
        """
        if isinstance(node, nodes.section):
            self._section_level += 1
            return

        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)
        if not isinstance(node, nodes.document):
            raise nodes.SkipNode

    def depart_section(self, node: nodes.Element) -> None:
        """
        Handle leaving section nodes by decreasing the section level.
        """
        del node
        self._section_level -= 1

    def depart_document(self, node: nodes.Element) -> None:
        """
        Output collected block tree as JSON at document end.
        """
        del node

        json_output = json.dumps(
            obj=[
                _serialize_block_with_children(block=block)
                for block in self._blocks
            ],
            indent=2,
            ensure_ascii=False,
        )
        self.body = json_output


@beartype
class NotionBuilder(TextBuilder):
    """
    Build Notion-compatible documents.
    """

    name = "notion"
    out_suffix = ".json"


@beartype
def _notion_register_pdf_include_directive(
    app: Sphinx,
) -> None:
    """
    Register the PDF include directive.
    """
    if isinstance(app.builder, NotionBuilder):
        sphinx_docutils.register_directive(
            name="pdf-include",
            directive=_NotionPdfIncludeDirective,
        )


@beartype
def _filter_ulem(record: logging.LogRecord) -> bool:
    """Filter out the warning about the `ulem package already being included`.

    This warning is emitted by ``sphinxcontrib-text-styles`` or
    ``sphinxnotes.strike`` when the ``ulem`` package is already included.

    Our users may use both of these extensions, so we filter out the
    warning.

    See:

    * https://github.com/sphinx-notes/strike/pull/10
    * https://github.com/martinpriestley/sphinxcontrib-text-styles/pull/1
    """
    msg = record.getMessage()
    return msg != "latex package 'ulem' already included"


@beartype
def setup(app: Sphinx) -> ExtensionMetadata:
    """
    Add the builder to Sphinx.
    """
    app.add_builder(builder=NotionBuilder)
    app.set_translator(name="notion", translator_class=NotionTranslator)

    app.connect(
        event="builder-inited",
        callback=_notion_register_pdf_include_directive,
    )

    logger = logging.getLogger(name="sphinx.sphinx.registry")
    logger.addFilter(filter=_filter_ulem)

    sphinxnotes.strike.SUPPORTED_BUILDERS.append(NotionBuilder)
    return {"parallel_read_safe": True}
