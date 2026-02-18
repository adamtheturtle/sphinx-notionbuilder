"""Tests for the _publish_to_notion event callback."""

import json
import os
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest
from sphinx.testing.util import SphinxTestApp
from ultimate_notion import Session
from ultimate_notion.blocks import Paragraph as UnoParagraph
from ultimate_notion.rich_text import text

from sphinx_notion import _publish_to_notion
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
    _publish_to_notion(
        app=app,
        exception=RuntimeError("build failed"),
    )


def test_publish_skips_when_disabled(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion returns immediately when notion_publish is False."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": False,
        },
    )
    _publish_to_notion(app=app, exception=None)


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
    app = make_app(
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": "abc123",
            "notion_page_title": "Test",
        },
    )
    _publish_to_notion(app=app, exception=None)


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
    _publish_to_notion(app=app, exception=None)


@_SKIP_DOCKER
def test_publish_success(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    notion_token: str,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """_publish_to_notion uploads the built JSON to the mock Notion
    API.
    """
    del notion_token
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": parent_page_id,
            "notion_page_title": "Upload Title",
        },
    )
    block_dicts = [
        UnoParagraph(
            text=text(text="Hello from publish test"),
        ).obj_ref.serialize_for_api()
    ]
    output_file = Path(app.outdir) / "index.json"
    output_file.write_text(
        data=json.dumps(obj=block_dicts),
        encoding="utf-8",
    )

    mock_session = Session(base_url=mock_api_base_url)
    with patch(target="sphinx_notion.Session", return_value=mock_session):
        _publish_to_notion(app=app, exception=None)


@_SKIP_DOCKER
def test_publish_propagates_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    notion_token: str,
    tmp_path: Path,
) -> None:
    """_publish_to_notion lets upload errors propagate to the caller."""
    del notion_token
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": "aaaa0000-0000-0000-0000-000000000001",
            "notion_page_title": "Upload Title",
        },
    )
    block_dicts: list[dict[str, object]] = []
    output_file = Path(app.outdir) / "index.json"
    output_file.write_text(
        data=json.dumps(obj=block_dicts),
        encoding="utf-8",
    )

    mock_session = Session(base_url=mock_api_base_url)
    with (
        patch(target="sphinx_notion.Session", return_value=mock_session),
        pytest.raises(expected_exception=PageHasSubpagesError),
    ):
        _publish_to_notion(app=app, exception=None)
