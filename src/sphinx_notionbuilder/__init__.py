"""
Sphinx Notion Builder.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from beartype import beartype
from docutils import nodes
from sphinx.builders.text import TextBuilder
from sphinx.writers.text import TextTranslator
from ultimate_notion.blocks import Paragraph as UnoParagraph

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata


@beartype
class NotionTranslator(TextTranslator):
    """
    Translate docutils nodes to Notion JSON.
    """

    def __init__(self, document: nodes.document, builder: TextBuilder) -> None:
        """
        Initialize the translator with storage for blocks.
        """
        super().__init__(document=document, builder=builder)
        self._blocks: list[UnoParagraph] = []

    def visit_paragraph(self, node: nodes.Element) -> None:
        """
        Handle paragraph nodes by creating Notion Paragraph blocks.
        """
        # Extract text content from the paragraph node
        text = cast("Any", node).astext()

        # Create a Notion Paragraph block
        block = UnoParagraph(text=text)
        self._blocks.append(block)

        # Skip default text processing
        raise nodes.SkipNode

    def visit_document(self, node: nodes.Element) -> None:  # noqa: ARG002
        """
        Initialize block collection at document start.
        """
        self._blocks = []

    def depart_document(self, node: nodes.Element) -> None:  # noqa: ARG002
        """
        Output collected blocks as JSON at document end.
        """
        # Convert blocks to JSON using Pydantic model_dump from obj_ref
        dumped_blocks = [
            cast("Any", block).obj_ref.model_dump(
                mode="json", by_alias=True, exclude_none=True
            )
            for block in self._blocks
        ]

        # Output as formatted JSON
        json_output = json.dumps(
            obj=dumped_blocks, indent=2, ensure_ascii=False
        )
        self.body = json_output


@beartype
class NotionBuilder(TextBuilder):
    """
    Build Notion-compatible documents.
    """

    name = "notion"
    out_suffix = ".json"
    default_translator_class: type[NotionTranslator] = NotionTranslator


@beartype
def setup(app: Sphinx) -> ExtensionMetadata:
    """
    Add the builder to Sphinx.
    """
    app.add_builder(builder=NotionBuilder)
    return {"parallel_read_safe": True}
