"""Tests for upload-to-Notion synchronization logic."""

from collections.abc import Sequence
from typing import Any, cast

import pytest
from ultimate_notion.blocks import Block
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

import sphinx_notion._upload as notion_upload


class _FakePage:
    """Minimal page double for upload tests."""

    def __init__(self, *, title: str, url: str) -> None:
        """Initialize a page with block storage and metadata fields."""
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
        """Record appended blocks and update the page block list."""
        self.append_calls.append((blocks, after))
        self.blocks.extend(blocks)


class _FakeParentPage:
    """Minimal parent page double for upload tests."""

    def __init__(self) -> None:
        """Initialize an empty parent page container."""
        self.subpages: list[_FakePage] = []


class _FakeSession:
    """Minimal session double exposing page access/creation methods."""

    def __init__(
        self,
        *,
        parent_page: _FakeParentPage,
        created_page: _FakePage,
    ) -> None:
        """Store parent and child page references for calls."""
        self.parent_page = parent_page
        self.created_page = created_page
        self.create_page_calls: list[tuple[object, str]] = []

    def get_page(self, *, page_ref: str) -> _FakeParentPage:
        """Return the configured parent page."""
        assert page_ref == "parent-page-id"
        return self.parent_page

    def create_page(self, *, parent: object, title: str) -> _FakePage:
        """Create and return the configured child page."""
        assert parent is self.parent_page
        self.create_page_calls.append((parent, title))
        self.created_page.title = title
        self.parent_page.subpages.append(self.created_page)
        return self.created_page


def _identity_block_with_uploaded_file(
    *,
    block: Block,
    session: object,
) -> Block:
    """Return block unchanged for tests that do not involve file
    uploads.
    """
    del session
    return block


def test_upload_to_notion_appends_new_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`upload_to_notion` appends new blocks when the page is empty."""
    parent_page = _FakeParentPage()
    created_page = _FakePage(
        title="",
        url="https://example.test/pages/uploaded",
    )
    fake_session = _FakeSession(
        parent_page=parent_page,
        created_page=created_page,
    )
    local_block = UnoParagraph(text=text(text="Hello from upload_to_notion"))

    monkeypatch.setattr(
        target=notion_upload,
        name="_block_with_uploaded_file",
        value=_identity_block_with_uploaded_file,
    )
    upload_to_notion_impl = cast(
        "Any", notion_upload.upload_to_notion
    ).__wrapped__

    uploaded_page = upload_to_notion_impl(
        session=fake_session,
        blocks=[local_block],
        parent_page_id="parent-page-id",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert uploaded_page is created_page
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
    rich_text = serialized_block["paragraph"]["rich_text"]
    assert rich_text[0]["plain_text"] == "Hello from upload_to_notion"
