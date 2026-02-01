"""Tests for the Sphinx builder."""

from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path

import docutils.utils
import pytest
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp

import sphinx_notion


def test_meta(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    Builder metadata and setup returns expected values for Sphinx
    integration.
    """
    builder_cls = sphinx_notion.NotionBuilder
    assert builder_cls.name == "notion"
    assert builder_cls.out_suffix == ".json"

    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(srcdir=srcdir)
    setup_result = sphinx_notion.setup(app=app)
    pkg_version = version(distribution_name="sphinx-notionbuilder")
    assert setup_result == {
        "parallel_read_safe": True,
        "version": pkg_version,
    }

    builder = builder_cls(app=app, env=app.env)
    document = docutils.utils.new_document(source_path=".")
    translator = sphinx_notion.NotionTranslator(
        document=document, builder=builder
    )
    translator.depart_document(node=document)
    assert translator.body == "[]"


def test_notion_publish_config_defaults(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Default configuration values are set correctly."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="extensions = ['sphinx_notion']")
    app = make_app(srcdir=srcdir)

    assert app.config.notion_publish is False
    assert app.config.notion_parent_page_id is None
    assert app.config.notion_parent_database_id is None
    assert app.config.notion_page_title is None
    assert app.config.notion_page_icon is None
    assert app.config.notion_page_cover_url is None
    assert app.config.notion_cancel_on_discussion is False


def test_notion_publish_requires_parent(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Enabling publish without parent raises error."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="extensions = ['sphinx_notion']")

    with pytest.raises(ExtensionError, match="neither notion_parent_page_id"):
        make_app(
            srcdir=srcdir,
            confoverrides={
                "notion_publish": True,
                "notion_page_title": "Test Page",
            },
        )


def test_notion_publish_mutually_exclusive_parents(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Setting both parent_page_id and parent_database_id raises error."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="extensions = ['sphinx_notion']")

    with pytest.raises(ExtensionError, match="mutually exclusive"):
        make_app(
            srcdir=srcdir,
            confoverrides={
                "notion_publish": True,
                "notion_parent_page_id": "abc123",
                "notion_parent_database_id": "def456",
                "notion_page_title": "Test Page",
            },
        )


def test_notion_publish_requires_title(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Enabling publish without title raises error."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="extensions = ['sphinx_notion']")

    with pytest.raises(ExtensionError, match="notion_page_title is not set"):
        make_app(
            srcdir=srcdir,
            confoverrides={
                "notion_publish": True,
                "notion_parent_page_id": "abc123",
            },
        )


def test_notion_publish_valid_config_with_page_id(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Valid configuration with parent_page_id passes validation."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="extensions = ['sphinx_notion']")

    app = make_app(
        srcdir=srcdir,
        confoverrides={
            "notion_publish": True,
            "notion_parent_page_id": "abc123",
            "notion_page_title": "Test Page",
        },
    )

    assert app.config.notion_publish is True
    assert app.config.notion_parent_page_id == "abc123"
    assert app.config.notion_page_title == "Test Page"


def test_notion_publish_valid_config_with_database_id(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Valid configuration with parent_database_id passes validation."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="extensions = ['sphinx_notion']")

    app = make_app(
        srcdir=srcdir,
        confoverrides={
            "notion_publish": True,
            "notion_parent_database_id": "def456",
            "notion_page_title": "Test Page",
            "notion_page_icon": "📚",
            "notion_page_cover_url": "https://example.com/cover.jpg",
            "notion_cancel_on_discussion": True,
        },
    )

    assert app.config.notion_publish is True
    assert app.config.notion_parent_database_id == "def456"
    assert app.config.notion_page_title == "Test Page"
    assert app.config.notion_page_icon == "📚"
    assert app.config.notion_page_cover_url == "https://example.com/cover.jpg"
    assert app.config.notion_cancel_on_discussion is True


def test_notion_publish_disabled_skips_validation(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """When publish is disabled, validation is skipped."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="extensions = ['sphinx_notion']")

    app = make_app(
        srcdir=srcdir,
        confoverrides={
            "notion_publish": False,
        },
    )

    assert app.config.notion_publish is False
