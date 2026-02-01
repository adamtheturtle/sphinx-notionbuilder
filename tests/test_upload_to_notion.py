"""Tests for the upload_to_notion function using WireMock."""

import time
from collections.abc import Generator
from typing import Any
from uuid import UUID

import pytest
import requests
from notion_client import Client as NotionClient
from notion_client.client import ClientOptions
from testcontainers.core.container import DockerContainer
from ultimate_notion import Session
from ultimate_notion.blocks import Paragraph

from _notion_scripts.upload import (  # pylint: disable=import-private-name
    PageHasDatabasesError,
    PageHasSubpagesError,
    upload_to_notion,
)

PARENT_PAGE_ID = "12345678-1234-1234-1234-123456789001"
NEW_PAGE_ID = "12345678-1234-1234-1234-123456789002"
EXISTING_PAGE_ID = "12345678-1234-1234-1234-123456789003"
SUBPAGE_ID = "12345678-1234-1234-1234-123456789004"
CHILD_DB_ID = "12345678-1234-1234-1234-123456789005"
NEW_BLOCK_ID = "12345678-1234-1234-1234-123456789006"
USER_ID = "12345678-1234-1234-1234-123456789007"


class WireMockContainer:
    """WireMock container wrapper for testing."""

    def __init__(self) -> None:
        """Initialize the WireMock container."""
        self._container: Any = DockerContainer(
            image="wiremock/wiremock:latest",
        )
        self._container.with_exposed_ports(8080)
        self._base_url: str = ""

    def start(self) -> None:
        """Start the WireMock container."""
        self._container.start()
        host: str = self._container.get_container_host_ip()
        port: str = self._container.get_exposed_port(8080)
        self._base_url = f"http://{host}:{port}"

        for _ in range(30):
            try:
                response = requests.get(
                    url=f"{self._base_url}/__admin/mappings",
                    timeout=5,
                )
                if response.status_code == 200:  # noqa: PLR2004
                    return
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)

        self._container.stop()
        msg = "WireMock container failed to start"
        raise RuntimeError(msg)

    def stop(self) -> None:
        """Stop the WireMock container."""
        self._container.stop()

    @property
    def base_url(self) -> str:
        """Get the base URL for the WireMock server."""
        return self._base_url

    def stub(
        self,
        *,
        method: str,
        url: str | None = None,
        url_pattern: str | None = None,
        status: int,
        json_body: dict[str, Any] | list[Any] | None = None,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Create a stub mapping in WireMock."""
        request_spec: dict[str, Any] = {"method": method}
        if url is not None:
            request_spec["url"] = url
        if url_pattern is not None:
            request_spec["urlPattern"] = url_pattern

        response_spec: dict[str, Any] = {"status": status}
        if json_body is not None:
            response_spec["jsonBody"] = json_body
        if body is not None:
            response_spec["body"] = body
        if headers is not None:
            response_spec["headers"] = headers
        else:
            response_spec["headers"] = {"Content-Type": "application/json"}

        mapping = {"request": request_spec, "response": response_spec}
        response = requests.post(
            url=f"{self._base_url}/__admin/mappings",
            json=mapping,
            timeout=5,
        )
        response.raise_for_status()

    def reset(self) -> None:
        """Reset all stub mappings."""
        requests.delete(
            url=f"{self._base_url}/__admin/mappings",
            timeout=5,
        )


@pytest.fixture(scope="module")
def fixture_wiremock() -> Generator[WireMockContainer, None, None]:
    """Provide a WireMock container for testing."""
    container = WireMockContainer()
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture
def fixture_wiremock_reset(
    fixture_wiremock: WireMockContainer,
) -> Generator[WireMockContainer, None, None]:
    """Reset WireMock stubs before each test and close Session after."""
    fixture_wiremock.reset()
    yield fixture_wiremock
    if Session._active_session is not None:  # noqa: SLF001
        Session._active_session.close()  # noqa: SLF001


def _page_response(
    *,
    page_id: str,
    parent_page_id: str | None = None,
    title: str = "Test Page",
    has_children: bool = False,
) -> dict[str, Any]:
    """Generate a Notion page response."""
    if parent_page_id is None:
        parent: dict[str, Any] = {"type": "workspace", "workspace": True}
    else:
        parent = {"type": "page_id", "page_id": parent_page_id}

    return {
        "object": "page",
        "id": page_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-01T00:00:00.000Z",
        "created_by": {"object": "user", "id": USER_ID},
        "last_edited_by": {"object": "user", "id": USER_ID},
        "cover": None,
        "icon": None,
        "parent": parent,
        "archived": False,
        "in_trash": False,
        "properties": {
            "title": {
                "id": "title",
                "type": "title",
                "title": [
                    {
                        "type": "text",
                        "text": {"content": title, "link": None},
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "default",
                        },
                        "plain_text": title,
                        "href": None,
                    }
                ],
            }
        },
        "url": f"https://www.notion.so/{page_id.replace('-', '')}",
        "public_url": None,
        "has_children": has_children,
    }


def _blocks_response(*, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a Notion blocks response."""
    return {
        "object": "list",
        "results": blocks,
        "next_cursor": None,
        "has_more": False,
        "type": "block",
        "block": {},
    }


def _paragraph_block(
    *,
    block_id: str,
    parent_page_id: str,
    text: str,
) -> dict[str, Any]:
    """Generate a Notion paragraph block."""
    return {
        "object": "block",
        "id": block_id,
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-01T00:00:00.000Z",
        "created_by": {"object": "user", "id": USER_ID},
        "last_edited_by": {"object": "user", "id": USER_ID},
        "has_children": False,
        "archived": False,
        "in_trash": False,
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text, "link": None},
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default",
                    },
                    "plain_text": text,
                    "href": None,
                }
            ],
            "color": "default",
        },
    }


def _child_page_block(
    *,
    block_id: str,
    parent_page_id: str,
    title: str,
) -> dict[str, Any]:
    """Generate a Notion child_page block."""
    return {
        "object": "block",
        "id": block_id,
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-01T00:00:00.000Z",
        "created_by": {"object": "user", "id": USER_ID},
        "last_edited_by": {"object": "user", "id": USER_ID},
        "has_children": False,
        "archived": False,
        "in_trash": False,
        "type": "child_page",
        "child_page": {"title": title},
    }


def _child_database_block(
    *,
    block_id: str,
    parent_page_id: str,
    title: str,
) -> dict[str, Any]:
    """Generate a Notion child_database block."""
    return {
        "object": "block",
        "id": block_id,
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-01T00:00:00.000Z",
        "created_by": {"object": "user", "id": USER_ID},
        "last_edited_by": {"object": "user", "id": USER_ID},
        "has_children": False,
        "archived": False,
        "in_trash": False,
        "type": "child_database",
        "child_database": {"title": title},
    }


def _database_response(
    *,
    database_id: str,
    parent_page_id: str,
    title: str,
) -> dict[str, Any]:
    """Generate a Notion database response."""
    return {
        "object": "database",
        "id": database_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-01T00:00:00.000Z",
        "created_by": {"object": "user", "id": USER_ID},
        "last_edited_by": {"object": "user", "id": USER_ID},
        "cover": None,
        "icon": None,
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "archived": False,
        "in_trash": False,
        "title": [
            {
                "type": "text",
                "text": {"content": title, "link": None},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default",
                },
                "plain_text": title,
                "href": None,
            }
        ],
        "description": [],
        "properties": {},
        "url": f"https://www.notion.so/{database_id.replace('-', '')}",
        "public_url": None,
        "is_inline": True,
    }


def test_upload_to_notion_creates_new_page(
    fixture_wiremock_reset: WireMockContainer,
) -> None:
    """Test that upload_to_notion creates a new page when none exists."""
    wm = fixture_wiremock_reset
    title = "Test Page"

    parent_page_id_pattern = PARENT_PAGE_ID.replace("-", "-?")
    new_page_id_pattern = NEW_PAGE_ID.replace("-", "-?")

    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{parent_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=PARENT_PAGE_ID,
            title="Parent Page",
            has_children=True,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/blocks/{parent_page_id_pattern}/children.*",
        status=200,
        json_body=_blocks_response(blocks=[]),
    )

    wm.stub(
        method="POST",
        url="/v1/pages",
        status=200,
        json_body=_page_response(
            page_id=NEW_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{new_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=NEW_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
        ),
    )

    wm.stub(
        method="PATCH",
        url_pattern=f"/v1/pages/{new_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=NEW_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/blocks/{new_page_id_pattern}/children.*",
        status=200,
        json_body=_blocks_response(blocks=[]),
    )

    wm.stub(
        method="PATCH",
        url_pattern=f"/v1/blocks/{new_page_id_pattern}/children",
        status=200,
        json_body=_blocks_response(
            blocks=[
                _paragraph_block(
                    block_id=NEW_BLOCK_ID,
                    parent_page_id=NEW_PAGE_ID,
                    text="Hello",
                )
            ]
        ),
    )

    client_options = ClientOptions(
        auth="fake-token",
        base_url=wm.base_url,
    )
    notion_client = NotionClient(options=client_options)
    session = Session(client=notion_client)

    blocks = [Paragraph(text="Hello")]

    page = upload_to_notion(
        session=session,
        blocks=blocks,
        parent_page_id=PARENT_PAGE_ID,
        parent_database_id=None,
        title=title,
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.id == UUID(NEW_PAGE_ID)  # type: ignore[misc]


def test_upload_to_notion_updates_existing_page(
    fixture_wiremock_reset: WireMockContainer,
) -> None:
    """Test that upload_to_notion updates an existing page."""
    wm = fixture_wiremock_reset
    title = "Test Page"

    parent_page_id_pattern = PARENT_PAGE_ID.replace("-", "-?")
    existing_page_id_pattern = EXISTING_PAGE_ID.replace("-", "-?")

    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{parent_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=PARENT_PAGE_ID,
            title="Parent Page",
            has_children=True,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/blocks/{parent_page_id_pattern}/children.*",
        status=200,
        json_body=_blocks_response(
            blocks=[
                _child_page_block(
                    block_id=EXISTING_PAGE_ID,
                    parent_page_id=PARENT_PAGE_ID,
                    title=title,
                )
            ]
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{existing_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=EXISTING_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
        ),
    )

    wm.stub(
        method="PATCH",
        url_pattern=f"/v1/pages/{existing_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=EXISTING_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/blocks/{existing_page_id_pattern}/children.*",
        status=200,
        json_body=_blocks_response(blocks=[]),
    )

    wm.stub(
        method="PATCH",
        url_pattern=f"/v1/blocks/{existing_page_id_pattern}/children",
        status=200,
        json_body=_blocks_response(
            blocks=[
                _paragraph_block(
                    block_id=NEW_BLOCK_ID,
                    parent_page_id=EXISTING_PAGE_ID,
                    text="Updated content",
                )
            ]
        ),
    )

    client_options = ClientOptions(
        auth="fake-token",
        base_url=wm.base_url,
    )
    notion_client = NotionClient(options=client_options)
    session = Session(client=notion_client)

    blocks = [Paragraph(text="Updated content")]

    page = upload_to_notion(
        session=session,
        blocks=blocks,
        parent_page_id=PARENT_PAGE_ID,
        parent_database_id=None,
        title=title,
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.id == UUID(EXISTING_PAGE_ID)  # type: ignore[misc]


def test_upload_to_notion_raises_page_has_subpages_error(
    fixture_wiremock_reset: WireMockContainer,
) -> None:
    """Test that PageHasSubpagesError is raised when page has subpages."""
    wm = fixture_wiremock_reset
    title = "Test Page"

    parent_page_id_pattern = PARENT_PAGE_ID.replace("-", "-?")
    existing_page_id_pattern = EXISTING_PAGE_ID.replace("-", "-?")

    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{parent_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=PARENT_PAGE_ID,
            title="Parent Page",
            has_children=True,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/blocks/{parent_page_id_pattern}/children.*",
        status=200,
        json_body=_blocks_response(
            blocks=[
                _child_page_block(
                    block_id=EXISTING_PAGE_ID,
                    parent_page_id=PARENT_PAGE_ID,
                    title=title,
                )
            ]
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{existing_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=EXISTING_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
            has_children=True,
        ),
    )

    wm.stub(
        method="PATCH",
        url_pattern=f"/v1/pages/{existing_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=EXISTING_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
            has_children=True,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/blocks/{existing_page_id_pattern}/children.*",
        status=200,
        json_body=_blocks_response(
            blocks=[
                _child_page_block(
                    block_id=SUBPAGE_ID,
                    parent_page_id=EXISTING_PAGE_ID,
                    title="Subpage",
                )
            ]
        ),
    )

    subpage_id_pattern = SUBPAGE_ID.replace("-", "-?")
    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{subpage_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=SUBPAGE_ID,
            parent_page_id=EXISTING_PAGE_ID,
            title="Subpage",
        ),
    )

    client_options = ClientOptions(
        auth="fake-token",
        base_url=wm.base_url,
    )
    notion_client = NotionClient(options=client_options)
    session = Session(client=notion_client)

    blocks = [Paragraph(text="Hello")]

    with pytest.raises(expected_exception=PageHasSubpagesError):
        upload_to_notion(
            session=session,
            blocks=blocks,
            parent_page_id=PARENT_PAGE_ID,
            parent_database_id=None,
            title=title,
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_upload_to_notion_raises_page_has_databases_error(
    fixture_wiremock_reset: WireMockContainer,
) -> None:
    """Test that PageHasDatabasesError is raised when page has
    databases.
    """
    wm = fixture_wiremock_reset
    title = "Test Page"

    parent_page_id_pattern = PARENT_PAGE_ID.replace("-", "-?")
    existing_page_id_pattern = EXISTING_PAGE_ID.replace("-", "-?")

    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{parent_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=PARENT_PAGE_ID,
            title="Parent Page",
            has_children=True,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/blocks/{parent_page_id_pattern}/children.*",
        status=200,
        json_body=_blocks_response(
            blocks=[
                _child_page_block(
                    block_id=EXISTING_PAGE_ID,
                    parent_page_id=PARENT_PAGE_ID,
                    title=title,
                )
            ]
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/pages/{existing_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=EXISTING_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
            has_children=True,
        ),
    )

    wm.stub(
        method="PATCH",
        url_pattern=f"/v1/pages/{existing_page_id_pattern}",
        status=200,
        json_body=_page_response(
            page_id=EXISTING_PAGE_ID,
            parent_page_id=PARENT_PAGE_ID,
            title=title,
            has_children=True,
        ),
    )

    wm.stub(
        method="GET",
        url_pattern=f"/v1/blocks/{existing_page_id_pattern}/children.*",
        status=200,
        json_body=_blocks_response(
            blocks=[
                _child_database_block(
                    block_id=CHILD_DB_ID,
                    parent_page_id=EXISTING_PAGE_ID,
                    title="Database",
                )
            ]
        ),
    )

    child_db_id_pattern = CHILD_DB_ID.replace("-", "-?")
    wm.stub(
        method="GET",
        url_pattern=f"/v1/databases/{child_db_id_pattern}",
        status=200,
        json_body=_database_response(
            database_id=CHILD_DB_ID,
            parent_page_id=EXISTING_PAGE_ID,
            title="Database",
        ),
    )

    client_options = ClientOptions(
        auth="fake-token",
        base_url=wm.base_url,
    )
    notion_client = NotionClient(options=client_options)
    session = Session(client=notion_client)

    blocks = [Paragraph(text="Hello")]

    with pytest.raises(expected_exception=PageHasDatabasesError):
        upload_to_notion(
            session=session,
            blocks=blocks,
            parent_page_id=PARENT_PAGE_ID,
            parent_database_id=None,
            title=title,
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )
