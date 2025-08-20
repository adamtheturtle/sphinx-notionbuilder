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
from ultimate_notion.blocks import (
    BulletedItem as UnoBulletedItem,
)
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
        """Handle paragraph nodes by creating Notion Paragraph blocks.

        Only process if not already processed as part of a list item.
        """
        rich_text = _create_rich_text_from_children(node=node)

        block = UnoParagraph(text="")
        block.rich_text = rich_text
        self._blocks.append(block)

        raise nodes.SkipNode

    def visit_document(self, node: nodes.Element) -> None:
        """
        Initialize block collection at document start.
        """
        del node
        self._blocks = []

    def visit_bullet_list(self, node: nodes.Element) -> None:
        """
        Handle bullet_list nodes by processing their list_item children.
        """
        # We don't create a block for the list itself, just process children
        del node

    def depart_bullet_list(self, node: nodes.Element) -> None:
        """
        Handle leaving bullet_list nodes.
        """
        del node

    def _process_list_item_recursive(
        self, node: nodes.list_item
    ) -> UnoBulletedItem:
        """
        Recursively process a list_item node and return a BulletedItem block.
        """
        # Extract text from the first paragraph child
        paragraph_text = ""
        nested_lists: list[nodes.bullet_list] = []

        for child in node.children:
            if isinstance(child, nodes.paragraph):
                paragraph_text = child.astext()
            elif isinstance(child, nodes.bullet_list):
                # Collect nested bullet lists for processing
                nested_lists.append(child)

        # Create the bulleted item
        block = UnoBulletedItem(text="")
        if paragraph_text:
            paragraph_node = next(
                c for c in node.children if isinstance(c, nodes.paragraph)
            )
            rich_text = _create_rich_text_from_children(node=paragraph_node)
            block.rich_text = rich_text

        # Process nested lists and add as children
        if nested_lists:
            children_blocks: list[UnoBulletedItem] = []
            for nested_list in nested_lists:
                for nested_item in nested_list.children:
                    if isinstance(nested_item, nodes.list_item):
                        # Recursively process nested list items
                        nested_block = self._process_list_item_recursive(
                            node=nested_item,
                        )
                        children_blocks.append(nested_block)

            # Set children on the block
            if children_blocks:
                type_data_class = type(block.obj_ref.bulleted_list_item)
                block.obj_ref.bulleted_list_item = type_data_class(
                    rich_text=block.obj_ref.bulleted_list_item.rich_text,
                    color=block.obj_ref.bulleted_list_item.color,
                    children=[child.obj_ref for child in children_blocks],
                )

        return block

    def visit_list_item(self, node: nodes.Element) -> None:
        """
        Handle list_item nodes by creating BulletedItem blocks.
        """
        # Extract text from the first paragraph child
        paragraph_text = ""
        nested_lists: list[nodes.bullet_list] = []

        for child in node.children:
            if isinstance(child, nodes.paragraph):
                rich_text = _create_rich_text_from_children(node=child)
                paragraph_text = child.astext()
            elif isinstance(child, nodes.bullet_list):
                # Collect nested bullet lists for processing
                nested_lists.append(child)

        # Create the main bulleted item
        block = UnoBulletedItem(text="")
        if paragraph_text:
            paragraph_node = next(
                c for c in node.children if isinstance(c, nodes.paragraph)
            )
            rich_text = _create_rich_text_from_children(node=paragraph_node)
            block.rich_text = rich_text

        # Process nested lists and add as children
        if nested_lists:
            children_blocks: list[UnoBulletedItem] = []
            for nested_list in nested_lists:
                for nested_item in nested_list.children:
                    if isinstance(nested_item, nodes.list_item):
                        # Recursively process nested list items
                        nested_block = self._process_list_item_recursive(
                            node=nested_item,
                        )
                        children_blocks.append(nested_block)

            # Set children on the block
            if children_blocks:
                type_data_class = type(block.obj_ref.bulleted_list_item)
                block.obj_ref.bulleted_list_item = type_data_class(
                    rich_text=block.obj_ref.bulleted_list_item.rich_text,
                    color=block.obj_ref.bulleted_list_item.color,
                    children=[child.obj_ref for child in children_blocks],
                )

        self._blocks.append(block)

        raise nodes.SkipNode

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
