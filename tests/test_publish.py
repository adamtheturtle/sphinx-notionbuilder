"""Tests for the _publish_to_notion event callback."""

import os
from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp

from sphinx_notion._upload import PageHasSubpagesError

_SKIP_DOCKER = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_TESTS") == "1",
    reason="SKIP_DOCKER_TESTS is set",
)


def test_publish_skips_on_exception(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion returns immediately when a build exception is
    given.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(
        srcdir=srcdir,
        confoverrides={"extensions": ["sphinx_notion"]},
    )
    app.emit("build-finished", RuntimeError("build failed"))


def test_publish_skips_when_disabled(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion returns immediately when notion_publish is False."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    (srcdir / "index.rst").write_text(data="Test\n====\n", encoding="utf-8")
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": False,
        },
    )
    app.build()


def test_publish_skips_when_not_notion_builder(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion returns when the active builder is not
    notion.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    (srcdir / "index.rst").write_text(data="Test\n====\n", encoding="utf-8")
    app = make_app(
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": "abc123",
            "notion_page_title": "Test",
        },
    )
    app.build()


def test_publish_skips_when_no_output_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion warns and returns when index.json does not exist."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": "abc123",
            "notion_page_title": "Test",
        },
    )
    app.emit("build-finished", None)


@_SKIP_DOCKER
def test_publish_success(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    notion_token: str,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """A Notion build with notion_publish=True uploads to the mock Notion
    API.
    """
    del notion_token
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    (srcdir / "index.rst").write_text(
        data="Test\n====\n\nHello from publish test.\n",
        encoding="utf-8",
    )
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": parent_page_id,
            "notion_page_title": "Upload Title",
            "notion_api_base_url": mock_api_base_url,
        },
    )
    app.build()
    assert app.statuscode == 0


@_SKIP_DOCKER
def test_publish_propagates_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    notion_token: str,
    tmp_path: Path,
) -> None:
    """A Notion build with a failing upload propagates the error."""
    del notion_token
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    (srcdir / "index.rst").write_text(data="", encoding="utf-8")
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": "aaaa0000-0000-0000-0000-000000000001",
            "notion_page_title": "Upload Title",
            "notion_api_base_url": mock_api_base_url,
        },
    )
    with pytest.raises(expected_exception=ExtensionError) as exc_info:
        app.build()
    assert isinstance(exc_info.value.__cause__, PageHasSubpagesError)
