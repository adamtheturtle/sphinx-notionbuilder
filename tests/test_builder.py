"""
Tests for the Sphinx builder.
"""

from collections.abc import Callable
from pathlib import Path

from sphinx.testing.util import SphinxTestApp

import sphinx_notionbuilder


def test_builder_meta(
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Test the metadata of the Notion builder.
    """
    builder_cls = sphinx_notionbuilder.NotionBuilder
    assert builder_cls.name == "notion"
    assert builder_cls.out_suffix == ".json"
    assert (
        builder_cls.default_translator_class
        == sphinx_notionbuilder.NotionTranslator
    )

    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(srcdir=srcdir)
    setup_result = sphinx_notionbuilder.setup(app=app)
    assert setup_result == {"parallel_read_safe": True}
