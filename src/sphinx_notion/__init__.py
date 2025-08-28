"""
Sphinx Notion Builder.
"""

import json
from functools import singledispatchmethod
from typing import Any

from beartype import beartype
from docutils import nodes
from docutils.nodes import NodeVisitor
from sphinx.application import Sphinx
from sphinx.builders.text import TextBuilder
from sphinx.util.typing import ExtensionMetadata
from sphinx_toolbox.collapse import CollapseNode
from ultimate_notion import Emoji
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
from ultimate_notion.core import NotionObject
from ultimate_notion.obj_api.core import GenericObject
from ultimate_notion.obj_api.enums import BGColor, CodeLang
from ultimate_notion.rich_text import Text, text

type _BlockTree = dict[tuple[NotionObject[Any], int], "_BlockTree"]


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
        else:
            new_text = text(
                text=child.astext(),
                bold=isinstance(child, nodes.strong),
                italic=isinstance(child, nodes.emphasis),
                code=isinstance(child, nodes.literal),
            )
        rich_text += new_text

    return rich_text


@beartype
def _extract_table_structure(
    node: nodes.table,
) -> tuple[int, nodes.row | None, list[nodes.row]]:
    """
    Return (n_cols, header_row, body_rows) for a table node.
    """
    header_row = None
    body_rows: list[nodes.row] = []
    n_cols = 0

    for child in node.children:
        assert isinstance(child, nodes.tgroup)
        n_cols = int(child.get(key="cols", failobj=0))
        for tgroup_child in child.children:
            if isinstance(tgroup_child, nodes.thead):
                for row in tgroup_child.children:
                    assert isinstance(row, nodes.row)
                    header_row = row
            elif isinstance(tgroup_child, nodes.tbody):
                for row in tgroup_child.children:
                    assert isinstance(row, nodes.row)
                    body_rows.append(row)

    return n_cols, header_row, body_rows


@beartype
def _cell_source_node(entry: nodes.Node) -> nodes.paragraph:
    """Return the paragraph child of an entry if present, else the entry.

    This isolates the small branch used when converting a table cell so
    the main table function becomes simpler.
    """
    paragraph_children = [
        c for c in entry.children if isinstance(c, nodes.paragraph)
    ]
    if len(paragraph_children) == 1:
        return paragraph_children[0]

    # If there are multiple children (multiple paragraphs or mixed nodes),
    # create a combined node that preserves all content. We insert a
    # double-newline text node between each top-level child to mimic
    # paragraph separation when converting to plain text/rich text.
    # Join the plain text of each top-level child with two newlines so
    # the resulting rich text becomes a single text fragment like
    # 'Cell 3\n\nCell 3' (matches test expectations).
    parts: list[str] = [c.astext() for c in entry.children]
    joined = "\n\n".join(parts)
    combined = nodes.paragraph()
    combined += nodes.Text(data=joined)
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
        self._block_tree: _BlockTree = {}
        self.body: str
        self._section_level = 0

    @beartype
    def _add_block_to_tree(
        self,
        block: NotionObject[Any],
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """Add a block to the block tree.

        First has to find the parent in the tree recursively.
        """
        block_key = (block, id(block))
        if not parent_path:
            self._block_tree[block_key] = {}
            return

        current_node = self._block_tree[parent_path[0]]

        for parent_key in parent_path[1:]:
            current_node = current_node[parent_key]
        current_node[block_key] = {}

    @beartype
    def _process_list_item_recursively(
        self,
        *,
        node: nodes.list_item,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Recursively process a list item node and return a BulletedItem.
        """
        paragraph = node.children[0]
        assert isinstance(paragraph, nodes.paragraph)
        rich_text = _create_rich_text_from_children(node=paragraph)
        block = UnoBulletedItem(text="placeholder")
        block.rich_text = rich_text
        self._add_block_to_tree(
            block=block,
            parent_path=parent_path,
        )

        bullet_only_msg = (
            "The only thing Notion supports within a bullet list is a "
            "bullet list"
        )
        assert isinstance(node, nodes.list_item)

        for child in node.children[1:]:
            assert isinstance(child, nodes.bullet_list), bullet_only_msg
            for nested_list_item in child.children:
                assert isinstance(nested_list_item, nodes.list_item), (
                    bullet_only_msg
                )
                self._process_list_item_recursively(
                    node=nested_list_item,
                    parent_path=[*parent_path, (block, id(block))],
                )

    @singledispatchmethod
    @beartype
    def _process_node_to_blocks(  # pylint: disable=no-self-use
        self,
        node: nodes.Element,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:  # pragma: no cover
        """
        Required function for ``singledispatch``.
        """
        del section_level
        del parent_path
        raise NotImplementedError(node)

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.table,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """Process rST table nodes by creating Notion Table blocks.

        This implementation delegates small branches to helpers which
        keeps the function body linear and easier to reason about.
        """
        del section_level

        n_cols, header_row, body_rows = _extract_table_structure(node=node)

        n_rows = 1 + len(body_rows) if header_row else len(body_rows)
        table = UnoTable(
            n_rows=n_rows, n_cols=n_cols, header_row=bool(header_row)
        )

        row_idx = 0
        if header_row is not None:
            for col_idx, entry in enumerate(iterable=header_row.children):
                source = _cell_source_node(entry=entry)
                table[row_idx, col_idx] = _create_rich_text_from_children(
                    node=source
                )
            row_idx += 1

        for body_row in body_rows:
            for col_idx, entry in enumerate(iterable=body_row.children):
                source = _cell_source_node(entry=entry)
                table[row_idx, col_idx] = _create_rich_text_from_children(
                    node=source
                )
            row_idx += 1

        self._add_block_to_tree(block=table, parent_path=parent_path)

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.paragraph,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process paragraph nodes by creating Notion Paragraph blocks.
        """
        del section_level
        rich_text = _create_rich_text_from_children(node=node)
        paragraph_block = UnoParagraph(text="")
        paragraph_block.rich_text = rich_text
        self._add_block_to_tree(block=paragraph_block, parent_path=parent_path)

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.block_quote,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process block quote nodes by creating Notion Quote blocks.
        """
        del section_level
        rich_text = _create_rich_text_from_children(node=node)
        quote_block = UnoQuote(text="")
        quote_block.rich_text = rich_text
        self._add_block_to_tree(block=quote_block, parent_path=parent_path)

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.literal_block,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process literal block nodes by creating Notion Code blocks.
        """
        del section_level
        code_text = _create_rich_text_from_children(node=node)
        pygments_lang = node.get(key="language", failobj="")
        language = _map_pygments_to_notion_language(
            pygments_lang=pygments_lang,
        )
        code_block = UnoCode(text=code_text, language=language)
        # By default, the code block has a color set (DEFAULT) which means
        # that there is no syntax highlighting.
        # See https://github.com/ultimate-notion/ultimate-notion/issues/93.
        for rich_text in code_text.rich_texts:  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            del rich_text.obj_ref.annotations  # pyright: ignore[reportUnknownMemberType]
        code_block.rich_text = code_text
        self._add_block_to_tree(block=code_block, parent_path=parent_path)

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.bullet_list,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process bullet list nodes by creating Notion BulletedItem blocks.
        """
        del section_level
        bullet_only_msg = (
            "The only thing Notion supports within a bullet list is a "
            "bullet list"
        )
        for list_item in node.children:
            assert isinstance(list_item, nodes.list_item), bullet_only_msg
            self._process_list_item_recursively(
                node=list_item,
                parent_path=parent_path,
            )

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.topic,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process topic nodes, specifically for table of contents.
        """
        del section_level  # Not used for topics
        # Later, we can support `.. topic::` directives, likely as
        # a callout with no icon.
        assert "contents" in node["classes"]
        toc_block = UnoTableOfContents()
        self._add_block_to_tree(block=toc_block, parent_path=parent_path)

    @_process_node_to_blocks.register
    def _(  # pylint: disable=no-self-use
        self,
        node: nodes.compound,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process Sphinx ``toctree`` nodes.
        """
        del node
        del section_level
        del parent_path
        # There are no specific Notion blocks for ``toctree`` nodes.
        # We need to support ``toctree`` in ``index.rst``.
        # Just ignore it.

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.title,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process title nodes by creating appropriate Notion heading blocks.
        """
        rich_text = _create_rich_text_from_children(node=node)

        heading_levels: dict[int, type[UnoHeading[Any]]] = {
            1: UnoHeading1,
            2: UnoHeading2,
            3: UnoHeading3,
        }
        heading_cls = heading_levels[section_level]
        block = heading_cls(text="")

        block.rich_text = rich_text
        self._add_block_to_tree(block=block, parent_path=parent_path)

    @beartype
    def _create_admonition_callout(
        self,
        node: nodes.Element,
        *,
        emoji: str,
        background_color: BGColor,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """Create a Notion Callout block for admonition nodes.

        The first child (typically a paragraph) becomes the callout
        text, and any remaining children become nested blocks within the
        callout.
        """
        block = UnoCallout(
            text="", icon=Emoji(emoji=emoji), color=background_color
        )

        self._add_block_to_tree(block=block, parent_path=parent_path)
        # Use the first child as the callout text
        first_child = node.children[0]
        if isinstance(first_child, nodes.paragraph):
            rich_text = _create_rich_text_from_children(node=first_child)
            block.rich_text = rich_text
            # Process remaining children as nested blocks
            children_to_process = node.children[1:]
        else:
            # If first child is not a paragraph, use empty text
            block.rich_text = Text.from_plain_text(text="")
            # Process all children as nested blocks (including the first)
            children_to_process = node.children

        # Process children as nested blocks
        for child in children_to_process:
            self._process_node_to_blocks(
                child,
                section_level=1,
                parent_path=[*parent_path, (block, id(block))],
            )

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.note,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process note admonition nodes by creating Notion Callout blocks.
        """
        del section_level
        self._create_admonition_callout(
            node=node,
            emoji="📝",
            background_color=BGColor.BLUE,
            parent_path=parent_path,
        )

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.warning,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process warning admonition nodes by creating Notion Callout blocks.
        """
        del section_level
        self._create_admonition_callout(
            node=node,
            emoji="⚠️",
            background_color=BGColor.YELLOW,
            parent_path=parent_path,
        )

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.tip,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process tip admonition nodes by creating Notion Callout blocks.
        """
        del section_level
        self._create_admonition_callout(
            node=node,
            emoji="💡",
            background_color=BGColor.GREEN,
            parent_path=parent_path,
        )

    @_process_node_to_blocks.register
    def _(
        self,
        node: CollapseNode,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process collapse nodes by creating Notion ToggleItem blocks.
        """
        del section_level

        title_text = node.attributes["label"]
        toggle_block = UnoToggleItem(text=title_text)
        self._add_block_to_tree(block=toggle_block, parent_path=parent_path)

        for child in node.children:
            self._process_node_to_blocks(
                child,
                section_level=1,
                parent_path=[*parent_path, (toggle_block, id(toggle_block))],
            )

    @_process_node_to_blocks.register
    def _(
        self,
        node: nodes.image,
        *,
        section_level: int,
        parent_path: list[tuple[NotionObject[Any], int]],
    ) -> None:
        """
        Process image nodes by creating Notion Image blocks.
        """
        del section_level

        image_url = node.attributes["uri"]

        # Create the image block (alt text is not used as caption)
        image_block = UnoImage(url=image_url, caption=None)
        self._add_block_to_tree(block=image_block, parent_path=parent_path)

    def visit_title(self, node: nodes.Element) -> None:
        """
        Handle title nodes by creating appropriate Notion heading blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_section(self, node: nodes.Element) -> None:
        """
        Handle section nodes by increasing the section level.
        """
        del node
        self._section_level += 1

    def depart_section(self, node: nodes.Element) -> None:
        """
        Handle leaving section nodes by decreasing the section level.
        """
        del node
        self._section_level -= 1

    def visit_paragraph(self, node: nodes.Element) -> None:
        """
        Handle paragraph nodes by creating Notion Paragraph blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_block_quote(self, node: nodes.Element) -> None:
        """
        Handle block quote nodes by creating Notion Quote blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_literal_block(self, node: nodes.Element) -> None:
        """
        Handle literal block nodes by creating Notion Code blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_bullet_list(self, node: nodes.Element) -> None:
        """
        Handle bullet list nodes by processing each list item.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_topic(self, node: nodes.Element) -> None:
        """
        Handle topic nodes, specifically for table of contents.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_note(self, node: nodes.Element) -> None:
        """
        Handle note admonition nodes by creating Notion Callout blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_warning(self, node: nodes.Element) -> None:
        """
        Handle warning admonition nodes by creating Notion Callout blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_tip(self, node: nodes.Element) -> None:
        """
        Handle tip admonition nodes by creating Notion Callout blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_table(self, node: nodes.Element) -> None:
        """
        Handle table nodes by creating Notion Table blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_compound(self, node: nodes.Element) -> None:
        """
        Handle compound admonition nodes by creating a table of contents block.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_CollapseNode(self, node: nodes.Element) -> None:  # pylint: disable=invalid-name  # noqa: N802
        """
        Handle collapse nodes by creating Notion ToggleItem blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_image(self, node: nodes.Element) -> None:
        """
        Handle image nodes by creating Notion Image blocks.
        """
        self._process_node_to_blocks(
            node,
            section_level=self._section_level,
            parent_path=[],
        )

        raise nodes.SkipNode

    def visit_document(self, node: nodes.Element) -> None:
        """
        Initialize block collection at document start.
        """
        assert self
        del node

    @beartype
    def _convert_block_tree_to_json(
        self,
        # `beartype` does not support recursive types, so we need to use a
        # simpler type.
        block_tree: dict[tuple[NotionObject[Any], int], Any],
    ) -> list[dict[str, Any]]:
        """
        Convert the block tree to a JSON-serializable format, ignoring IDs from
        tuples.
        """
        result: list[dict[str, Any]] = []
        for (block, _), subtree in block_tree.items():
            obj_ref = block.obj_ref
            assert isinstance(obj_ref, GenericObject)
            dumped_structure = {
                "block": obj_ref.serialize_for_api(),
                "children": self._convert_block_tree_to_json(
                    block_tree=subtree
                ),
            }
            result.append(dumped_structure)
        return result

    def depart_document(self, node: nodes.Element) -> None:
        """
        Output collected block tree as JSON at document end.
        """
        del node

        json_output = json.dumps(
            obj=self._convert_block_tree_to_json(block_tree=self._block_tree),
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
def setup(app: Sphinx) -> ExtensionMetadata:
    """
    Add the builder to Sphinx.
    """
    app.add_builder(builder=NotionBuilder)
    app.set_translator(name="notion", translator_class=NotionTranslator)

    return {"parallel_read_safe": True}
