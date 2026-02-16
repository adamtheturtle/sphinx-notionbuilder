"""Opt-in integration test for upload synchronization against a mock
API.
"""

import logging
import os
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path

import docker
import pytest
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_delay,
    wait_fixed,
)
from ultimate_notion import ExternalFile, Session
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

import sphinx_notion._upload as notion_upload

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_TESTS") == "1",
    reason="SKIP_DOCKER_TESTS is set",
)


@retry(
    stop=stop_after_delay(max_delay=120),
    wait=wait_fixed(wait=0.1),
    reraise=True,
)
def _wait_for_microcks(*, base_url: str) -> None:
    """Wait until the mock service API responds."""
    response = requests.get(
        url=f"{base_url}/api/services",
        timeout=2,
    )
    response.raise_for_status()


def _upload_openapi(*, base_url: str, openapi_path: Path) -> None:
    """Upload an OpenAPI artifact to the mock service."""
    with openapi_path.open(mode="rb") as file_obj:
        response = requests.post(
            url=f"{base_url}/api/artifact/upload?mainArtifact=true",
            files={"file": (openapi_path.name, file_obj, "application/yaml")},
            timeout=30,
        )

    if response.status_code not in (
        HTTPStatus.OK,
        HTTPStatus.CREATED,
    ):
        # Defensive: only reached if the Microcks upload endpoint fails.
        message = (  # pragma: no cover
            "OpenAPI upload failed with "
            f"{response.status_code}: {response.text}"
        )
        raise RuntimeError(message)  # pragma: no cover


@retry(
    stop=stop_after_delay(max_delay=30),
    wait=wait_fixed(wait=0.1),
    retry=retry_if_exception_type(exception_types=AssertionError),
    reraise=True,
)
def _wait_for_uploaded_service(
    *,
    base_url: str,
    service_name: str,
    service_version: str,
) -> None:
    """Wait until a specific service appears in the mock service."""
    response = requests.get(
        url=f"{base_url}/api/services",
        timeout=3,
    )
    response.raise_for_status()
    payload = response.text
    assert service_name in payload
    assert service_version in payload


@pytest.fixture(name="microcks_base_url", scope="module")
def fixture_microcks_base_url_fixture(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Provide a prepared mock service base URL."""
    openapi_path = (
        request.config.rootpath
        / "tests"
        / "notion_sandbox"
        / "notion-openapi.yml"
    )
    assert openapi_path.is_file()

    docker_client = docker.from_env()
    container = docker_client.containers.run(
        image="quay.io/microcks/microcks-uber:latest-native",
        detach=True,
        remove=True,
        ports={"8080/tcp": ("127.0.0.1", 0)},
    )
    container.reload()
    host_port = container.ports["8080/tcp"][0]["HostPort"]
    assert isinstance(host_port, str)
    base_url = f"http://127.0.0.1:{host_port}"

    _wait_for_microcks(base_url=base_url)
    _upload_openapi(base_url=base_url, openapi_path=openapi_path)
    _wait_for_uploaded_service(
        base_url=base_url,
        service_name="notion-api",
        service_version="1.1.0",
    )
    yield base_url
    container.remove(force=True)
    docker_client.close()


@pytest.fixture(name="notion_session")
def fixture_notion_session_fixture(
    *,
    microcks_base_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Session]:
    """Provide an `ultimate_notion` session wired to the mock API."""
    monkeypatch.setenv(name="NOTION_TOKEN", value="microcks-test-token")
    session = Session(base_url=f"{microcks_base_url}/rest/notion-api/1.1.0")
    yield session
    session.close()


@pytest.fixture(name="parent_page_id")
def fixture_parent_page_id() -> str:
    """The page ID used by the mock API fixtures."""
    return "59833787-2cf9-4fdf-8782-e53db20768a5"


def test_upload_to_notion_with_microcks(
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """Run upload synchronization against a mock API."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.title == "Upload Title"
    assert page.url == "https://www.notion.so/Upload-Title-59833787"
    assert str(object=page.id) == parent_page_id
    assert len(page.blocks) == 1
    assert isinstance(page.blocks[0], UnoParagraph)
    assert page.blocks[0].rich_text == "Hello from Microcks upload test"


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

    assert page.title == "Upload Title"
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
) -> None:
    """Upload with an emoji icon exercises the icon PATCH path."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon="\N{MEMO}",
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert page.icon == "\N{MEMO}"


def test_upload_with_cover_url(
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """Upload with a cover URL exercises the ExternalFile cover path."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url="https://example.com/cover.png",
        cancel_on_discussion=False,
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert isinstance(page.cover, ExternalFile)
    assert page.cover.url == "https://example.com/cover.png"
