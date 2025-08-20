"""
Sphinx Notion Builder.
"""

import json
from typing import TYPE_CHECKING, Any

import pydantic
from beartype import beartype
from docutils import nodes
from docutils.nodes import NodeVisitor
from sphinx.application import Sphinx
from sphinx.builders.text import TextBuilder
from sphinx.util.typing import ExtensionMetadata
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
from ultimate_notion.rich_text import Text, text

if TYPE_CHECKING:
    from ultimate_notion.core import NotionObject


def _create_rich_text_from_children(*, node: nodes.Element) -> Text:
    """
    Create Notion rich text from docutils node children.
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
class NotionTranslator(NodeVisitor):
    """
    Translate docutils nodes to Notion JSON.
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
        heading_level = self._section_level
        rich_text = _create_rich_text_from_children(node=node)

        heading_levels: dict[int, type[UnoHeading[Any]]] = {
            1: UnoHeading1,
            2: UnoHeading2,
            3: UnoHeading3,
        }
        heading_cls = heading_levels[heading_level]
        block = heading_cls(text="")

        block.rich_text = rich_text
        self._blocks.append(block)

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
        rich_text = _create_rich_text_from_children(node=node)

        block = UnoParagraph(text="")
        block.rich_text = rich_text
        self._blocks.append(block)

        raise nodes.SkipNode

    def visit_block_quote(self, node: nodes.Element) -> None:
        """
        Handle block quote nodes by creating Notion Quote blocks.
        """
        rich_text = _create_rich_text_from_children(node=node)

        block = UnoQuote(text="")
        block.rich_text = rich_text
        self._blocks.append(block)

        raise nodes.SkipNode

    def visit_topic(self, node: nodes.Element) -> None:
        """
        Handle topic nodes, specifically for table of contents.
        """
        # Later, we can support `.. topic::` directives, likely as
        # a callout with no icon.
        assert "contents" in node["classes"]
        block = UnoTableOfContents()
        self._blocks.append(block)

        raise nodes.SkipNode

    def visit_document(self, node: nodes.Element) -> None:
        """
        Initialize block collection at document start.
        """
        del node
        self._blocks = []

    def depart_document(self, node: nodes.Element) -> None:
        """
        Output collected blocks as JSON at document end.
        """
        del node
        dumped_blocks: list[dict[str, Any]] = []
        for block in self._blocks:
            obj_ref = block.obj_ref
            assert isinstance(obj_ref, pydantic.BaseModel)
            dumped_block: dict[str, Any] = obj_ref.model_dump(
                mode="json",
                by_alias=True,
                exclude_none=True,
            )
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
