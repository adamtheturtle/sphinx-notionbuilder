"""Opt-in integration test for upload synchronization against a mock
API.
"""

import json
import logging
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import docker
import pytest
import requests
from tenacity import (
    retry,
    stop_after_delay,
    wait_fixed,
)
from ultimate_notion import Session
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

import sphinx_notion._upload as notion_upload
from sphinx_notion._upload import (
    DiscussionsExistError,
    PageHasDatabasesError,
    PageHasSubpagesError,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_TESTS") == "1",
    reason="SKIP_DOCKER_TESTS is set",
)


@retry(
    stop=stop_after_delay(max_delay=30),
    wait=wait_fixed(wait=0.1),
    reraise=True,
)
def _wait_for_wiremock(*, base_url: str) -> None:
    """Wait until the WireMock admin API responds."""
    response = requests.get(
        url=f"{base_url}/__admin/mappings",
        timeout=2,
    )
    response.raise_for_status()


def _upload_wiremock_mappings(*, base_url: str, mappings_path: Path) -> None:
    """Upload mappings JSON to a WireMock instance."""
    with mappings_path.open(encoding="utf-8") as mappings_file:
        payload = json.load(fp=mappings_file)

    response = requests.post(
        url=f"{base_url}/__admin/mappings/import",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()


def _count_wiremock_requests(
    *,
    base_url: str,
    method: str,
    url_path: str,
    body_patterns: list[dict[str, str]] | None = None,
) -> int:
    """Count matching requests captured by WireMock."""
    request_body: dict[str, object] = {
        "method": method,
        "urlPath": url_path,
    }
    if body_patterns is not None:
        request_body["bodyPatterns"] = body_patterns

    response = requests.post(
        url=f"{base_url}/__admin/requests/count",
        json=request_body,
        timeout=30,
    )
    response.raise_for_status()
    count = response.json()["count"]
    assert isinstance(count, int)
    return count


def _page_update_url_path(*, page_id: str) -> str:
    """Return the page-update endpoint path for a page ID."""
    return f"/v1/pages/{page_id.replace('-', '')}"


@pytest.fixture(name="mock_api_base_url", scope="module")
def fixture_mock_api_base_url_fixture(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Provide a prepared mock service base URL."""
    mappings_path = (
        request.config.rootpath
        / "tests"
        / "notion_sandbox"
        / "notion-wiremock-stubs.json"
    )
    assert mappings_path.is_file()

    docker_client = docker.from_env()
    container = docker_client.containers.run(
        # This tag is arbitrary, but pinning is better than `latest`.
        image="wiremock/wiremock:3.9.1",
        detach=True,
        remove=True,
        ports={"8080/tcp": ("127.0.0.1", 0)},
    )
    try:
        container.reload()
        host_port = container.ports["8080/tcp"][0]["HostPort"]
        assert isinstance(host_port, str)
        base_url = f"http://127.0.0.1:{host_port}"

        _wait_for_wiremock(base_url=base_url)
        _upload_wiremock_mappings(
            base_url=base_url,
            mappings_path=mappings_path,
        )
        yield base_url
    finally:
        container.remove(force=True)
        docker_client.close()


@pytest.fixture(name="notion_session")
def fixture_notion_session_fixture(
    *,
    mock_api_base_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Session]:
    """Provide an `ultimate_notion` session wired to the mock API."""
    monkeypatch.setenv(name="NOTION_TOKEN", value="wiremock-test-token")
    session = Session(base_url=mock_api_base_url)
    yield session
    session.close()


@pytest.fixture(name="parent_page_id")
def fixture_parent_page_id() -> str:
    """The page ID used by the mock API fixtures."""
    return "59833787-2cf9-4fdf-8782-e53db20768a5"


@pytest.fixture(name="upload_title")
def fixture_upload_title() -> str:
    """A unique title for each upload test invocation."""
    return f"Upload Title {uuid4().hex}"


def test_upload_to_notion_with_wiremock(
    notion_session: Session,
    parent_page_id: str,
    upload_title: str,
) -> None:
    """It is possible to upload a page with the mock API."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title=upload_title,
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.title is not None
    assert str(object=page.title).startswith("Upload Title")
    assert page.url == "https://www.notion.so/Upload-Title-59833787"
    assert str(object=page.id) == parent_page_id
    assert len(page.blocks) == 1
    assert isinstance(page.blocks[0], UnoParagraph)
    assert page.blocks[0].rich_text == "Hello from WireMock upload test"


def test_upload_deletes_and_replaces_changed_blocks(
    caplog: pytest.LogCaptureFixture,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """Changed content triggers block deletion and re-upload."""
    with caplog.at_level(level=logging.INFO):
        page = notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[
                UnoParagraph(text=text(text="Different content triggers sync"))
            ],
            parent_page_id=parent_page_id,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=True,
        )

    assert page.title is not None
    assert str(object=page.title).startswith("Upload Title")
    assert str(object=page.id) == parent_page_id
    expected_match_log = (
        "0 prefix and 0 suffix blocks match, 1 to delete, 1 to upload"
    )
    assert expected_match_log in caplog.text
    assert "Deleting block 1/1" in caplog.text
    assert "Appending 1 blocks to page" in caplog.text


def test_upload_with_icon(
    notion_session: Session,
    parent_page_id: str,
    upload_title: str,
) -> None:
    """It is possible to upload a page with an emoji icon."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title=upload_title,
        icon="\N{MEMO}",
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.title is not None
    assert str(object=page.title).startswith("Upload Title")
    assert str(object=page.id) == parent_page_id
    assert page.icon == "\N{MEMO}"


def test_upload_with_cover_url(
    notion_session: Session,
    mock_api_base_url: str,
    parent_page_id: str,
    upload_title: str,
) -> None:
    """It is possible to upload a page with a cover URL."""
    cover_url = "https://example.com/cover.png"
    page_url_path = _page_update_url_path(page_id=parent_page_id)
    cover_body_patterns = [
        {"contains": '"cover":'},
        {"contains": '"type":"external"'},
        {"contains": f'"url":"{cover_url}"'},
    ]
    before_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path=page_url_path,
        body_patterns=cover_body_patterns,
    )

    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title=upload_title,
        icon=None,
        cover_path=None,
        cover_url=cover_url,
        cancel_on_discussion=False,
    )

    after_url_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path=page_url_path,
        body_patterns=cover_body_patterns,
    )

    assert after_url_count == before_count + 1


def test_upload_page_has_subpages_error(
    notion_session: Session,
) -> None:
    """PageHasSubpagesError raised when the target page has subpages."""
    with pytest.raises(expected_exception=PageHasSubpagesError):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[],
            parent_page_id="aaaa0000-0000-0000-0000-000000000001",
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_upload_page_has_databases_error(
    notion_session: Session,
) -> None:
    """PageHasDatabasesError raised when the target page has databases."""
    with pytest.raises(expected_exception=PageHasDatabasesError):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[],
            parent_page_id="bbbb0000-0000-0000-0000-000000000001",
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_upload_discussions_exist_error(
    notion_session: Session,
) -> None:
    """DiscussionsExistError raised when blocks to delete have discussions."""
    with pytest.raises(
        expected_exception=DiscussionsExistError,
        match=r"1 block.*1 discussion",
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[
                UnoParagraph(
                    text=text(text="Different content triggers sync"),
                ),
            ],
            parent_page_id="cccc0000-0000-0000-0000-000000000001",
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=True,
        )


def test_upload_with_database_parent(
    notion_session: Session,
    mock_api_base_url: str,
) -> None:
    """It is possible to upload a page to a database."""
    parent_database_id = "db000000-0000-0000-0000-000000000001"
    query_url_path = f"/v1/databases/{parent_database_id}/query"

    before_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="POST",
        url_path=query_url_path,
    )

    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        parent_page_id=None,
        parent_database_id=parent_database_id,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    after_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="POST",
        url_path=query_url_path,
    )

    assert after_count == before_count + 1


def test_upload_with_cover_path(
    notion_session: Session,
    mock_api_base_url: str,
    parent_page_id: str,
    tmp_path: Path,
    upload_title: str,
) -> None:
    """It is possible to upload a page with a local cover file."""
    cover_file = tmp_path / "cover.png"
    cover_file.write_bytes(data=b"fake-png-data")
    page_url_path = _page_update_url_path(page_id=parent_page_id)
    uploaded_file_id = "ff000000-0000-0000-0000-000000000001"
    cover_body_patterns = [
        {"contains": '"cover":'},
        {"contains": '"type":"file_upload"'},
        {"contains": f'"id":"{uploaded_file_id}"'},
    ]
    before_create_upload_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="POST",
        url_path="/v1/file_uploads",
    )
    before_send_upload_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="POST",
        url_path=f"/v1/file_uploads/{uploaded_file_id}/send",
    )
    before_cover_patch_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path=page_url_path,
        body_patterns=cover_body_patterns,
    )

    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title=upload_title,
        icon=None,
        cover_path=cover_file,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_create_upload_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="POST",
        url_path="/v1/file_uploads",
    )
    after_send_upload_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="POST",
        url_path=f"/v1/file_uploads/{uploaded_file_id}/send",
    )
    after_cover_patch_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path=page_url_path,
        body_patterns=cover_body_patterns,
    )
    assert after_create_upload_count == before_create_upload_count + 1
    assert after_send_upload_count == before_send_upload_count + 1
    assert after_cover_patch_count == before_cover_patch_count + 1
