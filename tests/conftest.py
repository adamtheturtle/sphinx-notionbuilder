"""Configuration for ``pytest``."""

import json
import os
from collections.abc import Iterator
from unittest.mock import patch
from uuid import uuid4

import pytest
import respx
from beartype import beartype
from ultimate_notion import Session
from wiremock_mock import add_wiremock_to_respx

pytest_plugins = "sphinx.testing.fixtures"  # pylint: disable=invalid-name

_BASE_URL = "https://mock.notion.test"


@pytest.fixture(name="respx_mock", scope="module")
def fixture_respx_mock(
    *,
    request: pytest.FixtureRequest,
) -> Iterator[respx.MockRouter]:
    """Provide a respx mock router loaded with WireMock stubs."""
    mappings_path = (
        request.config.rootpath
        / "tests"
        / "notion_sandbox"
        / "notion-wiremock-stubs.json"
    )
    assert mappings_path.is_file()

    with mappings_path.open(encoding="utf-8") as mappings_file:
        stubs = json.load(fp=mappings_file)

    mock = respx.MockRouter(assert_all_called=False)
    add_wiremock_to_respx(
        mock_obj=mock,
        stubs=stubs,
        base_url=_BASE_URL,
    )
    mock.start()
    try:
        yield mock
    finally:
        mock.stop()


@pytest.fixture(name="mock_api_base_url", scope="module")
def fixture_mock_api_base_url_fixture(
    *,
    respx_mock: respx.MockRouter,
) -> str:
    """Provide a prepared mock service base URL."""
    del respx_mock
    return _BASE_URL


@pytest.fixture(name="notion_token")
def fixture_notion_token() -> Iterator[str]:
    """Provide a token in environment variables for Ultimate Notion."""
    token = uuid4().hex
    with patch.dict(in_dict=os.environ, values={"NOTION_TOKEN": token}):
        yield token


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


@beartype
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """
    Apply the ``beartype`` decorator to all collected test
    functions.
    """
    for item in items:
        # All our tests are functions, for now
        assert isinstance(item, pytest.Function)
        item.obj = beartype(obj=item.obj)
