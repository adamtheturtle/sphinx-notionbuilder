"""
Sphinx Notion Builder.
"""

import json
from typing import Any

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
from ultimate_notion.core import NotionObject
from ultimate_notion.obj_api.blocks import Block, BulletedListItem
from ultimate_notion.rich_text import Text, text


def dump_notion_object(*, obj_ref: pydantic.BaseModel) -> dict[str, Any]:
    """Dump a Notion object to JSON format.

    All parameters are keyword-only to ensure explicit usage.
    """
    return obj_ref.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )


def get_bulleted_list_item_obj_ref(
    bulleted_item: NotionObject[Any],
) -> BulletedListItem:
    """Get the obj_ref from a BulletedItem with proper typing.

    This helper function provides type information that pyright can
    understand.
    """
    obj_ref = bulleted_item.obj_ref
    if not isinstance(obj_ref, BulletedListItem):
        msg = "Expected BulletedListItem"
        raise TypeError(msg)
    return obj_ref


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

    def visit_bullet_list(self, node: nodes.Element) -> None:
        """
        Handle bullet list nodes by processing list items.
        """
        for list_item in node.children:
            assert isinstance(list_item, nodes.list_item)
            block = self._create_bullet_item(list_item=list_item)
            self._blocks.append(block)

        raise nodes.SkipNode

    def _create_bullet_item(
        self, list_item: nodes.list_item
    ) -> UnoBulletedItem:
        """Create a BulletedItem from a list item.

        Handles recursive nesting for multiple levels.
        """
        paragraph_content = list_item.children[0]
        assert isinstance(paragraph_content, nodes.paragraph)
        nested_bullet_lists: list[nodes.bullet_list] = []

        for child in list_item.children[1:]:
            assert isinstance(child, nodes.bullet_list)
            nested_bullet_lists.append(child)

        rich_text = _create_rich_text_from_children(node=paragraph_content)

        block = UnoBulletedItem(text="")
        block.rich_text = rich_text

        # Store nested items as Block objects first
        nested_child_blocks: list[UnoBulletedItem] = []
        for nested_list in nested_bullet_lists:
            for nested_item in nested_list.children:
                assert isinstance(nested_item, nodes.list_item)
                nested_child_block = self._create_bullet_item(
                    list_item=nested_item
                )
                nested_child_blocks.append(nested_child_block)

        if nested_child_blocks:
            # Convert to Block objects that the API expects
            block_objects: list[Block] = []
            for nested_child_block in nested_child_blocks:
                nested_obj_ref = get_bulleted_list_item_obj_ref(
                    nested_child_block
                )
                child_json = dump_notion_object(obj_ref=nested_obj_ref)
                # Create a proper Block object from the JSON
                block_obj = Block.model_validate(child_json)
                block_objects.append(block_obj)

            obj_ref = get_bulleted_list_item_obj_ref(block)
            obj_ref.bulleted_list_item.children.extend(block_objects)
            obj_ref.has_children = True

        return block

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
            dumped_block: dict[str, Any] = dump_notion_object(obj_ref=obj_ref)
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
