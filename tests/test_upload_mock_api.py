"""Opt-in integration test for upload synchronization against a mock
API.
"""

import logging
import os
import time
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path

import docker
import pytest
import requests
from docker.client import DockerClient
from docker.errors import DockerException
from docker.models.containers import Container
from ultimate_notion import Session
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

import sphinx_notion._upload as notion_upload

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_TESTS") == "1",
    reason="SKIP_DOCKER_TESTS is set",
)


def _start_microcks(*, docker_client: DockerClient) -> Container:
    """Start mock service container and return the container handle."""
    return docker_client.containers.run(
        image="quay.io/microcks/microcks-uber:latest-native",
        detach=True,
        remove=True,
        ports={"8080/tcp": ("127.0.0.1", 0)},
    )


def _get_microcks_port(*, container: Container) -> str:
    """Get the host port assigned by Docker for the mock service."""
    container.reload()
    host_port = container.ports["8080/tcp"][0]["HostPort"]
    assert isinstance(host_port, str)
    return host_port


def _stop_microcks(
    *,
    docker_client: DockerClient,
    container: Container,
) -> None:
    """Stop the mock service container and close the docker client."""
    try:
        container.remove(force=True)
    except DockerException:
        pass
    finally:
        docker_client.close()


def _wait_for_microcks(*, base_url: str, timeout_seconds: int) -> None:
    """Wait until the mock service API responds."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = requests.get(
                url=f"{base_url}/api/services",
                timeout=2,
            )
            if response.status_code == HTTPStatus.OK:
                return
        except requests.RequestException:
            pass
        time.sleep(0.1)

    message = f"Mock service did not become ready: {base_url}"
    raise RuntimeError(message)


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
        message = (
            "OpenAPI upload failed with "
            f"{response.status_code}: {response.text}"
        )
        raise RuntimeError(message)


def _wait_for_uploaded_service(
    *,
    base_url: str,
    service_name: str,
    service_version: str,
    timeout_seconds: int,
) -> None:
    """Wait until a specific service appears in the mock service."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = requests.get(
            url=f"{base_url}/api/services",
            timeout=3,
        )
        response.raise_for_status()
        payload = response.text
        if service_name in payload and service_version in payload:
            return
        time.sleep(0.1)

    message = (
        f"Service '{service_name}' version '{service_version}' "
        "did not appear in the mock service."
    )
    raise RuntimeError(message)


@pytest.fixture(name="microcks_base_url")
def fixture_microcks_base_url_fixture(
    # This `yield` fixture tears down docker resources.
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

    try:
        docker_client: DockerClient = docker.from_env()
    except DockerException:
        pytest.skip(reason="Docker is not available for this test.")

    container = _start_microcks(docker_client=docker_client)
    port = _get_microcks_port(container=container)
    base_url = f"http://127.0.0.1:{port}"

    _wait_for_microcks(base_url=base_url, timeout_seconds=120)
    _upload_openapi(base_url=base_url, openapi_path=openapi_path)
    _wait_for_uploaded_service(
        base_url=base_url,
        service_name="notion-api",
        service_version="1.1.0",
        timeout_seconds=30,
    )
    yield base_url
    _stop_microcks(docker_client=docker_client, container=container)


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
    caplog: pytest.LogCaptureFixture,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """Upload with an emoji icon exercises the icon PATCH path."""
    with caplog.at_level(level=logging.INFO):
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
    assert "Setting page icon to '\N{MEMO}'" in caplog.text


def test_upload_with_cover_url(
    caplog: pytest.LogCaptureFixture,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """Upload with a cover URL exercises the ExternalFile cover path."""
    with caplog.at_level(level=logging.INFO):
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
    expected_cover_log = (
        "Setting page cover to 'https://example.com/cover.png'"
    )
    assert expected_cover_log in caplog.text
