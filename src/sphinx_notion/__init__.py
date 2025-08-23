"""
Sphinx Notion Builder.
"""

import json
from functools import singledispatch
from typing import Any

from beartype import beartype
from docutils import nodes
from docutils.nodes import NodeVisitor
from sphinx.application import Sphinx
from sphinx.builders.text import TextBuilder
from sphinx.util.typing import ExtensionMetadata
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
from ultimate_notion.rich_text import Text, text


def _process_list_item_recursively(
    node: nodes.list_item,
    depth: int,
) -> UnoBulletedItem:
    """
    Recursively process a list item node and return a BulletedItem.
    """
    paragraph = node.children[0]
    assert isinstance(paragraph, nodes.paragraph)
    rich_text = _create_rich_text_from_children(node=paragraph)
    block = UnoBulletedItem(text="placeholder")
    block.rich_text = rich_text

    bullet_only_msg = (
        "The only thing Notion supports within a bullet list is a bullet list"
    )
    max_notion_depth = 1
    if depth >= max_notion_depth:
        # This limit is described in https://developers.notion.com/reference/patch-block-children
        #
        # "For blocks that allow children, we allow up to two levels of
        # nesting in a single request."
        #
        # Note that the top level bullet-list is the "child" of the "body"
        # so there is really only one level of nesting in the Notion API
        # in one request.
        for child in node.children[1:]:
            assert isinstance(child, nodes.bullet_list), bullet_only_msg
            max_levels = max_notion_depth + 1
            msg = (
                f"Nested bullet point at depth {max_levels + 1} "
                f"exceeds Notion API limit of {max_levels} levels."
            )
            raise ValueError(msg)

    for child in node.children[1:]:
        assert isinstance(child, nodes.bullet_list), bullet_only_msg
        for nested_list_item in child.children:
            assert isinstance(nested_list_item, nodes.list_item), (
                bullet_only_msg
            )
            nested_block = _process_list_item_recursively(
                node=nested_list_item,
                depth=depth + 1,
            )
            # Remove pyright ignore once we have
            # https://github.com/ultimate-notion/ultimate-notion/issues/94.
            block.obj_ref.value.children.append(nested_block.obj_ref)  # pyright: ignore[reportUnknownMemberType]

    return block


def _create_rich_text_from_children(*, node: nodes.Element) -> Text:
    """
    Create Notion rich text from ``docutils`` node children.
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


@singledispatch
def _process_node_to_blocks(
    node: nodes.Element,
    *,
    section_level: int,
) -> list[NotionObject[Any]]:  # pragma: no cover
    """
    Required function for ``singledispatch``.
    """
    del node
    del section_level
    raise NotImplementedError


@_process_node_to_blocks.register
def _(node: nodes.paragraph, *, section_level: int) -> list[NotionObject[Any]]:
    """
    Process paragraph nodes by creating Notion Paragraph blocks.
    """
    del section_level
    rich_text = _create_rich_text_from_children(node=node)
    paragraph_block = UnoParagraph(text="")
    paragraph_block.rich_text = rich_text
    return [paragraph_block]


@_process_node_to_blocks.register
def _(
    node: nodes.block_quote, *, section_level: int
) -> list[NotionObject[Any]]:
    """
    Process block quote nodes by creating Notion Quote blocks.
    """
    del section_level
    rich_text = _create_rich_text_from_children(node=node)
    quote_block = UnoQuote(text="")
    quote_block.rich_text = rich_text
    return [quote_block]


@_process_node_to_blocks.register
def _(
    node: nodes.literal_block, *, section_level: int
) -> list[NotionObject[Any]]:
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
    del code_text.rich_texts[0].obj_ref.annotations  # pyright: ignore[reportUnknownMemberType]
    code_block.rich_text = code_text
    return [code_block]


@_process_node_to_blocks.register
def _(node: nodes.list_item, *, section_level: int) -> list[NotionObject[Any]]:
    """
    Process list item nodes by creating BulletedItem blocks.
    """
    del section_level
    return [_process_list_item_recursively(node=node, depth=0)]


@_process_node_to_blocks.register
def _(
    node: nodes.bullet_list,
    *,
    section_level: int,
) -> list[NotionObject[Any]]:
    """
    Process bullet list nodes by creating Notion BulletedItem blocks.
    """
    del section_level
    del node
    # We don't create a block for the list itself,
    # just process the children (list items)
    return []


@_process_node_to_blocks.register
def _(node: nodes.topic, *, section_level: int) -> list[NotionObject[Any]]:
    """
    Process topic nodes, specifically for table of contents.
    """
    del section_level  # Not used for topics
    # Later, we can support `.. topic::` directives, likely as
    # a callout with no icon.
    assert "contents" in node["classes"]
    return [UnoTableOfContents()]


@_process_node_to_blocks.register
def _(node: nodes.title, *, section_level: int) -> list[NotionObject[Any]]:
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
    return [block]


def _create_admonition_callout(
    node: nodes.Element,
    *,
    emoji: str,
    color: Color,
) -> list[NotionObject[Any]]:
    """Create a Notion Callout block for admonition nodes.

    The first child (typically a paragraph) becomes the callout text,
    and any remaining children become nested blocks within the callout.
    """
    block = UnoCallout(text="", icon=Emoji(emoji=emoji), color=color)

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
        for child_block in list(
            _process_node_to_blocks(
                child,
                section_level=1,
            )
        ):
            # Add nested blocks as children to the callout
            # Remove pyright ignore once we have
            # https://github.com/ultimate-notion/ultimate-notion/issues/94.
            block.obj_ref.value.children.append(child_block.obj_ref)  # pyright: ignore[reportUnknownMemberType]

    return [block]


@_process_node_to_blocks.register
def _(node: nodes.note, *, section_level: int) -> list[NotionObject[Any]]:
    """
    Process note admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(node=node, emoji="📝", color=Color.BLUE)


@_process_node_to_blocks.register
def _(node: nodes.warning, *, section_level: int) -> list[NotionObject[Any]]:
    """
    Process warning admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(node=node, emoji="⚠️", color=Color.YELLOW)


@_process_node_to_blocks.register
def _(node: nodes.tip, *, section_level: int) -> list[NotionObject[Any]]:
    """
    Process tip admonition nodes by creating Notion Callout blocks.
    """
    del section_level
    return _create_admonition_callout(node=node, emoji="💡", color=Color.GREEN)


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
        self._blocks: list[NotionObject[Any]] = []
        self.body: str
        self._section_level = 0

    def visit_title(self, node: nodes.Element) -> None:
        """
        Handle title nodes by creating appropriate Notion heading blocks.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)

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
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)
        raise nodes.SkipNode

    def visit_block_quote(self, node: nodes.Element) -> None:
        """
        Handle block quote nodes by creating Notion Quote blocks.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)
        raise nodes.SkipNode

    def visit_literal_block(self, node: nodes.Element) -> None:
        """
        Handle literal block nodes by creating Notion Code blocks.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)
        raise nodes.SkipNode

    def visit_bullet_list(self, node: nodes.Element) -> None:
        """
        Handle bullet list nodes by processing each list item.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)

    def depart_bullet_list(self, node: nodes.Element) -> None:
        """
        Handle leaving bullet list nodes.
        """
        assert self
        del node

    def visit_list_item(self, node: nodes.Element) -> None:
        """
        Handle list item nodes by creating Notion BulletedItem blocks.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)
        raise nodes.SkipNode

    def visit_topic(self, node: nodes.Element) -> None:
        """
        Handle topic nodes, specifically for table of contents.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)
        raise nodes.SkipNode

    def visit_note(self, node: nodes.Element) -> None:
        """
        Handle note admonition nodes by creating Notion Callout blocks.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)

        raise nodes.SkipNode

    def visit_warning(self, node: nodes.Element) -> None:
        """
        Handle warning admonition nodes by creating Notion Callout blocks.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)

        raise nodes.SkipNode

    def visit_tip(self, node: nodes.Element) -> None:
        """
        Handle tip admonition nodes by creating Notion Callout blocks.
        """
        blocks = _process_node_to_blocks(
            node,
            section_level=self._section_level,
        )
        self._blocks.extend(blocks)

        raise nodes.SkipNode

    def visit_document(self, node: nodes.Element) -> None:
        """
        Initialize block collection at document start.
        """
        assert self
        del node

    def depart_document(self, node: nodes.Element) -> None:
        """
        Output collected blocks as JSON at document end.
        """
        del node
        dumped_blocks: list[dict[str, Any]] = []
        for block in self._blocks:
            obj_ref = block.obj_ref
            assert isinstance(obj_ref, GenericObject)
            dumped_block = obj_ref.serialize_for_api()
            dumped_blocks.append(dumped_block)

        json_output = json.dumps(
            obj=dumped_blocks,
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
