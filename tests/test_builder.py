"""
Tests for the Sphinx builder.
"""

from collections.abc import Callable
from pathlib import Path

import docutils.utils
from sphinx.testing.util import SphinxTestApp

import sphinx_notion


def test_meta(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test the metadata of the Notion builder.
    """
    builder_cls = sphinx_notion.NotionBuilder
    assert builder_cls.name == "notion"
    assert builder_cls.out_suffix == ".json"

    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(srcdir=srcdir)
    setup_result = sphinx_notion.setup(app=app)
    assert setup_result == {"parallel_read_safe": True}

    builder = builder_cls(app=app, env=app.env)
    document = docutils.utils.new_document(source_path=".")
    translator = sphinx_notion.NotionTranslator(
        document=document, builder=builder
    )
    translator.depart_document(node=document)
    assert translator.body == "[]"
