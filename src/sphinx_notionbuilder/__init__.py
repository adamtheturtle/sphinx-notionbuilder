"""
Sphinx Notion Builder.
"""

import json
from collections.abc import Iterator, Set as AbstractSet
from typing import TYPE_CHECKING, Any

import pydantic
from beartype import beartype
from docutils import nodes
from docutils.io import StringOutput
from docutils.nodes import NodeVisitor
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.osutil import _last_modified_time
from sphinx.util.typing import ExtensionMetadata
from ultimate_notion.blocks import Paragraph as UnoParagraph
from ultimate_notion.rich_text import Text, text

if TYPE_CHECKING:
    from ultimate_notion.core import NotionObject

logger = logging.getLogger(__name__)


@beartype
class NotionTranslator(NodeVisitor):
    """
    Translate docutils nodes to Notion JSON.
    """

    def __init__(
        self, document: nodes.document, builder: "NotionBuilder"
    ) -> None:
        """
        Initialize the translator with storage for blocks.
        """
        del builder
        super().__init__(document=document)
        self._blocks: list[NotionObject[Any]] = []
        self.body: str

    def _process_inline_nodes(self, node: nodes.Element) -> Text:
        """Process inline nodes to create rich text with formatting.

        Returns a Text object that can be used with ultimate-notion.
        """
        # Start with empty text
        result_text = Text.from_plain_text(text="")

        for child in node.children:
            if isinstance(child, nodes.Text):
                # Plain text node
                plain_text = text(text=str(object=child))
                result_text += plain_text
            elif isinstance(child, nodes.strong):
                # Bold text
                bold_content = child.astext()
                bold_text = text(text=bold_content, bold=True)
                result_text += bold_text
            elif isinstance(child, nodes.emphasis):
                # Italic text
                italic_content = child.astext()
                italic_text = text(text=italic_content, italic=True)
                result_text += italic_text
            elif isinstance(child, nodes.literal):
                # Inline code
                code_content = child.astext()
                code_text = text(text=code_content, code=True)
                result_text += code_text
            else:
                # For other node types, just extract text
                plain_content = child.astext()
                plain_text = text(text=plain_content)
                result_text += plain_text

        return result_text

    def visit_paragraph(self, node: nodes.Element) -> None:
        """
        Handle paragraph nodes by creating Notion Paragraph blocks.
        """
        assert isinstance(node, nodes.paragraph)

        # Process inline formatting
        rich_text = self._process_inline_nodes(node=node)

        # Create paragraph with rich text
        block = UnoParagraph(text="dummy")  # temporary text
        block.rich_text = rich_text  # set the actual rich text
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
class NotionBuilder(Builder):
    """
    Build Notion-compatible documents.
    """

    name = "notion"
    format = "notion"
    epilog = __("The Notion JSON files are in %(outdir)s.")
    out_suffix = ".json"
    allow_parallel = True
    # Override the default translator class
    default_translator_class = NotionTranslator  # type: ignore[assignment]

    current_docname: str | None = None

    def init(self) -> None:
        """
        Initialize the builder.
        """
        # section numbers for headings in the currently visited document
        self.secnumbers: dict[str, tuple[int, ...]] = {}
        # Writer will be initialized in prepare_writing
        self.writer: NotionWriter

    def get_outdated_docs(self) -> Iterator[str]:
        """
        Return an iterable of output files that are outdated.
        """
        for docname in self.env.found_docs:
            if docname not in self.env.all_docs:
                yield docname
                continue
            targetname = self.outdir / (docname + self.out_suffix)
            try:
                targetmtime = _last_modified_time(targetname)
            except (OSError, FileNotFoundError):
                targetmtime = 0
            try:
                srcmtime = _last_modified_time(self.env.doc2path(docname))
                if srcmtime > targetmtime:
                    yield docname
            except OSError:
                # source doesn't exist anymore
                pass

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        """
        Return the target URI for a document name.
        """
        del docname, typ  # Not used in this implementation
        return ""

    def prepare_writing(self, docnames: AbstractSet[str]) -> None:
        """
        Prepare for writing documents.
        """
        del docnames  # Not used in this implementation
        # Create a writer for this builder
        self.writer = NotionWriter(self)

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        """
        Write the output file for a document.
        """
        self.current_docname = docname
        self.secnumbers = self.env.toc_secnumbers.get(docname, {})
        destination = StringOutput(encoding="utf-8")
        self.writer.write(doctree, destination)
        out_file_name = self.outdir / (docname + self.out_suffix)
        out_file_name.parent.mkdir(parents=True, exist_ok=True)
        try:
            with out_file_name.open("w", encoding="utf-8") as f:
                f.write(self.writer.output)
        except OSError as err:
            logger.warning(__("error writing file %s: %s"), out_file_name, err)

    def finish(self) -> None:
        """
        Finish the building process.
        """


@beartype
class NotionWriter:
    """
    Writer that uses NotionTranslator to generate Notion JSON.
    """

    def __init__(self, builder: NotionBuilder) -> None:
        """
        Initialize the writer with a builder.
        """
        self.builder = builder
        self.output: str = ""

    def write(
        self, document: nodes.document, destination: StringOutput
    ) -> None:
        """
        Write a document using the NotionTranslator.
        """
        del destination  # Not used in this implementation
        visitor = self.builder.create_translator(document, self.builder)
        assert isinstance(visitor, NotionTranslator)
        document.walkabout(visitor)
        self.output = visitor.body


@beartype
def setup(app: Sphinx) -> ExtensionMetadata:
    """
    Add the builder to Sphinx.
    """
    app.add_builder(builder=NotionBuilder)
    return {"parallel_read_safe": True}
