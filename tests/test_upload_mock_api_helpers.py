"""Tests for the helper functions in test_upload_mock_api.

These exercise the error / timeout paths that are never reached during
a successful Docker-based integration test.  They do not require Docker.
"""

import time
from http import HTTPStatus
from pathlib import Path
from typing import NoReturn
from unittest.mock import MagicMock

import pytest
import requests

from tests.test_upload_mock_api import (
    upload_openapi,
    wait_for_microcks,
    wait_for_uploaded_service,
)


def _noop_sleep(_duration: float) -> None:
    """No-op replacement for time.sleep in tests."""


def test_wait_for_microcks_timeout() -> None:
    """Immediate timeout when deadline is already in the past."""
    with pytest.raises(
        expected_exception=RuntimeError,
        match="did not become ready",
    ):
        wait_for_microcks(base_url="http://127.0.0.1:1", timeout_seconds=0)


def test_wait_for_microcks_request_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RequestException is caught and the function eventually times
    out.
    """
    monotonic_values = iter([0, 0.5, 2])
    monkeypatch.setattr(
        target=time,
        name="monotonic",
        value=lambda: next(monotonic_values),
    )
    monkeypatch.setattr(target=time, name="sleep", value=_noop_sleep)

    def raise_request_exception(**_kwargs: str) -> NoReturn:
        """Always raise RequestException."""
        raise requests.RequestException

    monkeypatch.setattr(
        target=requests,
        name="get",
        value=raise_request_exception,
    )

    with pytest.raises(
        expected_exception=RuntimeError,
        match="did not become ready",
    ):
        wait_for_microcks(base_url="http://127.0.0.1:1", timeout_seconds=1)


def test_upload_openapi_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Non-OK/CREATED response raises RuntimeError."""
    openapi_file = tmp_path / "test.yml"
    openapi_file.write_text(data="openapi: '3.0.0'")

    fake_response = MagicMock()
    fake_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    fake_response.text = "Internal Server Error"

    def fake_post(**_kwargs: str) -> MagicMock:
        """Return a fake error response."""
        return fake_response

    monkeypatch.setattr(target=requests, name="post", value=fake_post)

    with pytest.raises(
        expected_exception=RuntimeError,
        match="OpenAPI upload failed",
    ):
        upload_openapi(
            base_url="http://127.0.0.1:1",
            openapi_path=openapi_file,
        )


def test_wait_for_uploaded_service_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout when the expected service never appears."""
    monotonic_values = iter([0, 0.5, 2])
    monkeypatch.setattr(
        target=time,
        name="monotonic",
        value=lambda: next(monotonic_values),
    )
    monkeypatch.setattr(target=time, name="sleep", value=_noop_sleep)

    fake_response = MagicMock()
    fake_response.status_code = HTTPStatus.OK
    fake_response.text = "no matching service here"

    def fake_get(**_kwargs: str) -> MagicMock:
        """Return a fake response without the target service."""
        return fake_response

    monkeypatch.setattr(target=requests, name="get", value=fake_get)

    with pytest.raises(
        expected_exception=RuntimeError,
        match="did not appear",
    ):
        wait_for_uploaded_service(
            base_url="http://127.0.0.1:1",
            service_name="my-service",
            service_version="1.0",
            timeout_seconds=1,
        )
