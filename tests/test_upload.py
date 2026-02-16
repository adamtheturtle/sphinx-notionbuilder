"""Tests for the upload script."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_regressions.file_regression import FileRegressionFixture
from ultimate_notion import Session
from ultimate_notion.blocks import Block
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

import _notion_scripts.upload as upload_script
import sphinx_notion._upload as notion_upload
from _notion_scripts.upload import main  # pylint: disable=import-private-name


class _FakePage:
    """Minimal page double for upload testing."""

    def __init__(self, *, title: str, url: str) -> None:
        """Initialize a page with mutable block and metadata fields."""
        self.title = title
        self.url = url
        self.icon: object | None = None
        self.cover: object | None = None
        self.subpages: list[_FakePage] = []
        self.subdbs: list[object] = []
        self.blocks: list[Block] = []
        self.append_calls: list[tuple[Sequence[Block], Block | None]] = []

    def append(
        self,
        *,
        blocks: Sequence[Block],
        after: Block | None = None,
    ) -> None:
        """Record and apply appended blocks."""
        self.append_calls.append((blocks, after))
        self.blocks.extend(blocks)


class _FakeParentPage:
    """Minimal parent page double for upload testing."""

    def __init__(self) -> None:
        """Initialize an empty parent page container."""
        self.subpages: list[_FakePage] = []


class _FakeSession(Session):
    """Session double compatible with beartype checks."""

    def __init__(
        self, *, parent_page: _FakeParentPage, created_page: _FakePage
    ) -> None:
        """Store references used by `get_page` and `create_page`."""
        self.parent_page = parent_page
        self.created_page = created_page
        self.create_page_calls: list[tuple[object, str]] = []

    def get_page(self, *, page_ref: str) -> _FakeParentPage:
        """Return the configured parent page."""
        assert page_ref == "parent-page-id"
        return self.parent_page

    def create_page(self, *, parent: object, title: str) -> _FakePage:
        """Return the configured created page."""
        assert parent is self.parent_page
        self.create_page_calls.append((parent, title))
        self.created_page.title = title
        self.parent_page.subpages.append(self.created_page)
        return self.created_page


def test_help(file_regression: FileRegressionFixture) -> None:
    """Expected help text is shown.

    This help text is defined in files.
    To update these files, run ``pytest`` with the ``--regen-all`` flag.
    """
    runner = CliRunner()
    arguments = ["--help"]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    file_regression.check(contents=result.output)


def test_upload_invokes_upload_to_notion_logic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upload command calls into upload logic and appends blocks."""
    parent_page = _FakeParentPage()
    created_page = _FakePage(
        title="",
        url="https://example.test/pages/uploaded",
    )
    fake_session = _FakeSession(
        parent_page=parent_page,
        created_page=created_page,
    )

    block = UnoParagraph(text=text(text="Hello from CLI upload"))
    file_path = tmp_path / "upload.json"
    file_path.write_text(
        data=json.dumps([block.obj_ref.serialize_for_api()]),
        encoding="utf-8",
    )

    monkeypatch.setattr(upload_script, "Session", lambda: fake_session)
    monkeypatch.setattr(
        upload_script,
        "upload_to_notion",
        notion_upload.upload_to_notion.__wrapped__,
    )

    runner = CliRunner()
    arguments = [
        "--file",
        str(file_path),
        "--parent-page-id",
        "parent-page-id",
        "--title",
        "Upload Title",
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert (
        result.output.strip()
        == "Uploaded page: 'Upload Title' (https://example.test/pages/uploaded)"
    )
    assert created_page.icon is None
    assert created_page.cover is None
    assert len(fake_session.create_page_calls) == 1

    assert len(created_page.append_calls) == 1
    (uploaded_blocks, after_block) = created_page.append_calls[0]
    assert after_block is None
    assert len(uploaded_blocks) == 1
    uploaded_block = uploaded_blocks[0]
    assert isinstance(uploaded_block, UnoParagraph)
    serialized_block = uploaded_block.obj_ref.serialize_for_api()
    assert isinstance(serialized_block, dict)
    rich_text: Any = serialized_block["paragraph"]["rich_text"]
    assert rich_text[0]["plain_text"] == "Hello from CLI upload"
