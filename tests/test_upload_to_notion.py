"""Tests for the Microcks mock server with notion-sandbox."""

import time
from collections.abc import Generator
from typing import Any

import pytest
import requests
import yaml
from beartype import beartype
from testcontainers.core.container import DockerContainer

# Example page ID from notion-sandbox OpenAPI spec
# This ID triggers a success response in Microcks
_EXAMPLE_PAGE_ID = "59833787-2cf9-4fdf-8782-e53db20768a5"

# URL to the notion-sandbox OpenAPI spec
_OPENAPI_SPEC_URL = (
    "https://raw.githubusercontent.com/naftiko/notion-sandbox"
    "/main/openapi/notion-openapi.yml"
)


@beartype
class MicrocksContainer:
    """Microcks container wrapper for testing."""

    def __init__(self) -> None:
        """Initialize the Microcks container."""
        self._container: Any = DockerContainer(
            image="quay.io/microcks/microcks-uber:latest",
        )
        self._container.with_exposed_ports(8080)
        self._base_url: str = ""

    def start(self) -> None:
        """Start the Microcks container."""
        self._container.start()
        host: str = self._container.get_container_host_ip()
        port: str = self._container.get_exposed_port(8080)
        self._base_url = f"http://{host}:{port}"

        # Wait for Microcks to be ready
        for _ in range(60):
            try:
                response = requests.get(
                    url=f"{self._base_url}/api/health",
                    timeout=5,
                )
                if response.status_code == 200:  # noqa: PLR2004
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        else:
            self._container.stop()
            msg = "Microcks container failed to start"
            raise RuntimeError(msg)

        # Import the notion-sandbox OpenAPI spec
        self._import_openapi_spec()

    def _import_openapi_spec(self) -> None:
        """Import the notion-sandbox OpenAPI spec into Microcks.

        The notion_client library prepends /v1 to all API paths, but the
        notion-sandbox spec has paths like /pages/{page_id}. We modify
        the spec to add /v1 prefix to all paths so Microcks serves them
        at URLs that match what notion_client requests.
        """
        # Download the OpenAPI spec
        spec_response = requests.get(url=_OPENAPI_SPEC_URL, timeout=30)
        spec_response.raise_for_status()

        # Parse and modify the spec to add /v1 prefix to all paths
        spec: dict[str, Any] = yaml.safe_load(  # type: ignore[no-untyped-call]
            stream=spec_response.content,
        )
        original_paths: dict[str, Any] = spec.get("paths", {})
        modified_paths: dict[str, Any] = {}
        for path, path_item in original_paths.items():
            modified_paths[f"/v1{path}"] = path_item
        spec["paths"] = modified_paths

        # Convert back to YAML
        modified_spec: str = yaml.dump(  # type: ignore[no-untyped-call]
            data=spec,
            default_flow_style=False,
        )

        # Upload to Microcks
        files = {
            "file": (
                "notion-openapi.yml",
                modified_spec.encode(),
                "application/x-yaml",
            )
        }
        upload_response = requests.post(
            url=f"{self._base_url}/api/artifact/upload",
            files=files,
            timeout=30,
        )
        upload_response.raise_for_status()

        # Wait for the spec to be processed
        time.sleep(2)

    def stop(self) -> None:
        """Stop the Microcks container."""
        self._container.stop()

    @property
    def mock_url(self) -> str:
        """Get the mock API base URL.

        Microcks serves mocks at /rest/{service}/{version}.
        The service name comes from the OpenAPI spec info.title
        and version from info.version (URL-encoded).
        """
        return f"{self._base_url}/rest/notion-api/1.1.0"


@pytest.fixture(scope="module")
def fixture_microcks() -> Generator[MicrocksContainer, None, None]:
    """Provide a Microcks container for testing."""
    container = MicrocksContainer()
    container.start()
    try:
        yield container
    finally:
        container.stop()


def test_microcks_serves_notion_api_mocks(
    fixture_microcks: MicrocksContainer,
) -> None:
    """Test that Microcks serves mock responses for Notion API endpoints.

    Uses the notion-sandbox example responses from Microcks.
    This verifies the mock infrastructure works correctly.

    Note: We use direct HTTP requests because the notion-sandbox
    example responses don't perfectly match what ultimate_notion's
    Pydantic models expect, causing validation errors.
    """
    # Make a direct request to the mock endpoint
    response = requests.get(
        url=f"{fixture_microcks.mock_url}/v1/pages/{_EXAMPLE_PAGE_ID}",
        headers={
            "Authorization": "Bearer fake-token",
            "Notion-Version": "2022-06-28",
        },
        timeout=30,
    )

    # Verify we got a successful response with page data
    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["object"] == "page"
    assert data["id"] == _EXAMPLE_PAGE_ID
