"""
Sphinx Notion Builder.
"""

from beartype import beartype
from sphinx.application import Sphinx
from sphinx.builders.text import TextBuilder
from sphinx.util.typing import ExtensionMetadata
from sphinx.writers.text import TextTranslator


@beartype
class NotionTranslator(TextTranslator):
    """
    Translate docutils nodes to Notion JSON.
    """


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
