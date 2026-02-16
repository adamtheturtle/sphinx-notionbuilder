"""Opt-in Microcks integration test for upload synchronization."""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, cast

import pytest
import requests
from ultimate_notion import Session
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

import sphinx_notion._upload as notion_upload

_MICROCKS_IMAGE = "quay.io/microcks/microcks-uber:latest-native"
_MICROCKS_SERVICE_NAME = "notion-api"
_MICROCKS_SERVICE_VERSION = "1.1.0"
_PARENT_PAGE_ID = "59833787-2cf9-4fdf-8782-e53db20768a5"
_HTTP_OK = 200
_OPENAPI_PATH = Path(__file__).parent / "notion_sandbox" / "notion-openapi.yml"


def _is_enabled() -> bool:
    """Return whether Microcks integration tests are explicitly
    enabled.
    """
    return os.environ.get("RUN_MICROCKS_TESTS") == "1"


def _find_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    assert isinstance(port, int)
    return port


def _docker_is_available() -> bool:
    """Return whether the Docker CLI and daemon are available."""
    if shutil.which(cmd="docker") is None:
        return False

    result = subprocess.run(
        args=["docker", "info"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _start_microcks(*, port: int) -> str:
    """Start Microcks and return its container ID."""
    result = subprocess.run(
        args=[
            "docker",
            "run",
            "--detach",
            "--rm",
            "--publish",
            f"{port}:8080",
            _MICROCKS_IMAGE,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    container_id = result.stdout.strip()
    assert container_id
    return container_id


def _stop_microcks(*, container_id: str) -> None:
    """Stop a Microcks container."""
    subprocess.run(
        args=["docker", "rm", "--force", container_id],
        check=False,
        capture_output=True,
        text=True,
    )


def _wait_for_microcks(*, base_url: str, timeout_seconds: int = 120) -> None:
    """Wait until the Microcks API responds."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = requests.get(
                url=f"{base_url}/api/services",
                timeout=2,
            )
            if response.status_code == _HTTP_OK:
                return
        except requests.RequestException:
            pass
        time.sleep(1)

    message = f"Microcks did not become ready: {base_url}"
    raise RuntimeError(message)


def _upload_openapi(*, base_url: str, openapi_path: Path) -> None:
    """Upload an OpenAPI artifact to Microcks."""
    with openapi_path.open(mode="rb") as file_obj:
        response = requests.post(
            url=f"{base_url}/api/artifact/upload?mainArtifact=true",
            files={"file": (openapi_path.name, file_obj, "application/yaml")},
            timeout=30,
        )

    if response.status_code not in (200, 201):
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
    timeout_seconds: int = 30,
) -> None:
    """Wait until a specific service appears in Microcks."""
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
        time.sleep(1)

    message = (
        f"Service '{service_name}' version '{service_version}' "
        "did not appear in Microcks."
    )
    raise RuntimeError(message)


def test_upload_to_notion_with_microcks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run upload synchronization against a Microcks-backed Notion
    mock.
    """
    if not _is_enabled():
        pytest.skip(reason="Set RUN_MICROCKS_TESTS=1 to enable this test.")

    if not _docker_is_available():
        pytest.skip(reason="Docker daemon is not available for Microcks.")

    assert _OPENAPI_PATH.is_file()

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    container_id = _start_microcks(port=port)
    try:
        _wait_for_microcks(base_url=base_url)
        _upload_openapi(base_url=base_url, openapi_path=_OPENAPI_PATH)
        _wait_for_uploaded_service(
            base_url=base_url,
            service_name=_MICROCKS_SERVICE_NAME,
            service_version=_MICROCKS_SERVICE_VERSION,
        )

        monkeypatch.setenv(name="NOTION_TOKEN", value="microcks-test-token")

        session = Session(
            base_url=(
                f"{base_url}/rest/"
                f"{_MICROCKS_SERVICE_NAME}/{_MICROCKS_SERVICE_VERSION}"
            )
        )
        try:
            upload_to_notion_impl = cast(
                "Any", notion_upload.upload_to_notion
            ).__wrapped__

            page = upload_to_notion_impl(
                session=session,
                blocks=[
                    UnoParagraph(
                        text=text(text="Hello from Microcks upload test")
                    )
                ],
                parent_page_id=_PARENT_PAGE_ID,
                parent_database_id=None,
                title="Upload Title",
                icon=None,
                cover_path=None,
                cover_url=None,
                cancel_on_discussion=False,
            )
        finally:
            session.close()

        assert page.title == "Upload Title"
        assert page.url == "https://www.notion.so/Upload-Title-59833787"
    finally:
        _stop_microcks(container_id=container_id)
