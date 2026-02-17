"""Configuration for ``pytest``."""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import docker
import pytest
import requests
from beartype import beartype
from tenacity import (
    retry,
    stop_after_delay,
    wait_fixed,
)
from ultimate_notion import Session

pytest_plugins = "sphinx.testing.fixtures"  # pylint: disable=invalid-name


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


@pytest.fixture(name="mock_api_base_url", scope="module")
def fixture_mock_api_base_url_fixture(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Provide a prepared mock service base URL."""
    if os.environ.get("SKIP_DOCKER_TESTS") == "1":
        pytest.skip(reason="SKIP_DOCKER_TESTS is set")

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


@pytest.fixture(name="notion_token")
def fixture_notion_token() -> Iterator[str]:
    """Provide a token in env vars for Ultimate Notion."""
    token = uuid4().hex
    previous_token = os.environ.get("NOTION_TOKEN")
    os.environ["NOTION_TOKEN"] = token
    try:
        yield token
    finally:
        if previous_token is None:
            os.environ.pop("NOTION_TOKEN", None)
        else:
            os.environ["NOTION_TOKEN"] = previous_token


@pytest.fixture(name="notion_session")
def fixture_notion_session_fixture(
    *,
    mock_api_base_url: str,
    notion_token: str,
) -> Iterator[Session]:
    """Provide an `ultimate_notion` session wired to the mock API."""
    del notion_token
    session = Session(base_url=mock_api_base_url)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(name="parent_page_id")
def fixture_parent_page_id() -> str:
    """The page ID used by the mock API fixtures."""
    return "59833787-2cf9-4fdf-8782-e53db20768a5"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """
    Apply the ``beartype`` decorator to all collected test
    functions.
    """
    for item in items:
        # All our tests are functions, for now
        assert isinstance(item, pytest.Function)
        item.obj = beartype(obj=item.obj)
