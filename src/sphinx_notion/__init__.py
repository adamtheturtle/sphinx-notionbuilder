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
from ultimate_notion.blocks import Paragraph as UnoParagraph
from ultimate_notion.rich_text import Text, text

if TYPE_CHECKING:
    from ultimate_notion.core import NotionObject


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

    def _process_inline_nodes(self, node: nodes.Element) -> Text:
        """
        Process inline nodes to create rich text with formatting.
        """
        result_text = Text.from_plain_text(text="")

        for child in node.children:
            if isinstance(child, nodes.Text):
                plain_text = text(text=str(object=child))
                result_text += plain_text
            elif isinstance(child, nodes.strong):
                bold_content = child.astext()
                bold_text = text(text=bold_content, bold=True)
                result_text += bold_text
            elif isinstance(child, nodes.emphasis):
                italic_content = child.astext()
                italic_text = text(text=italic_content, italic=True)
                result_text += italic_text
            elif isinstance(child, nodes.literal):
                code_content = child.astext()
                code_text = text(text=code_content, code=True)
                result_text += code_text
            else:
                plain_content = child.astext()
                plain_text = text(text=plain_content)
                result_text += plain_text

        return result_text

    def visit_paragraph(self, node: nodes.Element) -> None:
        """
        Handle paragraph nodes by creating Notion Paragraph blocks.
        """
        assert isinstance(node, nodes.paragraph)

        rich_text = self._process_inline_nodes(node=node)

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
