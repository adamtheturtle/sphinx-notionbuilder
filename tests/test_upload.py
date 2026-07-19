"""Tests for the upload script."""

import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import respx
from click.testing import CliRunner, Result
from pytest_regressions.file_regression import FileRegressionFixture
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

from _notion_scripts.upload import main  # pylint: disable=import-private-name
from sphinx_notion._upload import PageTitleAmbiguousError
from tests._wiremock import count_page_metadata_clear_requests


def _write_blocks_file(
    *,
    tmp_path: Path,
    block_dicts: list[dict[str, Any]],
) -> Path:
    """Write block payload JSON to a temporary file."""
    blocks_file = tmp_path / "blocks.json"
    blocks_file.write_text(
        data=json.dumps(obj=block_dicts),
        encoding="utf-8",
    )
    return blocks_file


def _invoke_upload(
    *,
    blocks_file: Path,
    parent_page_id: str | None,
    mock_api_base_url: str,
    cancel_on_discussion: bool = False,
    page_id: str | None = None,
) -> Result:
    """Invoke the upload CLI against the mock Notion API."""
    runner = CliRunner()
    arguments = [
        "--file",
        str(object=blocks_file),
        "--title",
        "Upload Title",
        "--notion-api-base-url",
        mock_api_base_url,
    ]
    if parent_page_id is not None:
        arguments.extend(["--parent-page-id", parent_page_id])
    if cancel_on_discussion:
        arguments.append("--cancel-on-discussion")
    if page_id is not None:
        arguments.extend(["--page-id", page_id])
    return runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )


def _paragraph_blocks(
    *,
    text_content: str,
) -> list[dict[str, Any]]:
    """Create serialized paragraph blocks."""
    return [
        UnoParagraph(
            text=text(text=text_content),
        ).obj_ref.serialize_for_api()
    ]


def test_help(file_regression: FileRegressionFixture) -> None:
    """Expected help text is shown.

    This help text is defined in files.
    To update these files, run ``pytest`` with the ``--regen-all`` flag.
    """
    runner = CliRunner()
    arguments = ["--help"]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    file_regression.check(contents=result.output)


def test_upload_success(
    *,
    mock_api_base_url: str,
    notion_token: str,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """Uploading through the CLI reports success."""
    assert notion_token
    blocks_file = _write_blocks_file(
        tmp_path=tmp_path,
        block_dicts=_paragraph_blocks(
            text_content="Hello from WireMock upload test",
        ),
    )

    result = _invoke_upload(
        blocks_file=blocks_file,
        parent_page_id=parent_page_id,
        mock_api_base_url=mock_api_base_url,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.output == (
        "Uploaded page: 'Upload Title' "
        "(https://www.notion.so/Upload-Title-59833787)\n"
    )


def test_upload_page_has_subpages_error(
    *,
    mock_api_base_url: str,
    notion_token: str,
    tmp_path: Path,
) -> None:
    """A useful error is shown when the target page has subpages."""
    assert notion_token
    blocks_file = _write_blocks_file(
        tmp_path=tmp_path,
        block_dicts=[],
    )

    result = _invoke_upload(
        blocks_file=blocks_file,
        parent_page_id="aaaa0000-0000-0000-0000-000000000001",
        mock_api_base_url=mock_api_base_url,
    )

    assert result.exit_code == 1
    assert "This page has subpages." in result.output


def test_upload_page_has_databases_error(
    *,
    mock_api_base_url: str,
    notion_token: str,
    tmp_path: Path,
) -> None:
    """A useful error is shown when the target page has databases."""
    assert notion_token
    blocks_file = _write_blocks_file(
        tmp_path=tmp_path,
        block_dicts=[],
    )

    result = _invoke_upload(
        blocks_file=blocks_file,
        parent_page_id="bbbb0000-0000-0000-0000-000000000001",
        mock_api_base_url=mock_api_base_url,
    )

    assert result.exit_code == 1
    assert "This page has databases." in result.output


def test_upload_discussions_exist_error(
    *,
    mock_api_base_url: str,
    notion_token: str,
    tmp_path: Path,
) -> None:
    """The discussion error message is forwarded to the CLI."""
    assert notion_token
    blocks_file = _write_blocks_file(
        tmp_path=tmp_path,
        block_dicts=_paragraph_blocks(
            text_content="Different content triggers sync",
        ),
    )

    result = _invoke_upload(
        blocks_file=blocks_file,
        parent_page_id="cccc0000-0000-0000-0000-000000000001",
        mock_api_base_url=mock_api_base_url,
        cancel_on_discussion=True,
    )

    assert result.exit_code == 1
    assert "discussion" in result.output.lower()


def test_upload_with_page_id(
    *,
    mock_api_base_url: str,
    notion_token: str,
    parent_page_id: str,
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """Uploading to a page given by ID reports success."""
    assert notion_token
    blocks_file = _write_blocks_file(
        tmp_path=tmp_path,
        block_dicts=_paragraph_blocks(
            text_content="Hello from WireMock upload test",
        ),
    )

    clears_before = count_page_metadata_clear_requests(
        mock=respx_mock,
        page_id=parent_page_id,
    )
    result = _invoke_upload(
        blocks_file=blocks_file,
        parent_page_id=None,
        mock_api_base_url=mock_api_base_url,
        page_id=parent_page_id,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.output == (
        "Uploaded page: 'Upload Title' "
        "(https://www.notion.so/Upload-Title-59833787)\n"
    )
    assert (
        count_page_metadata_clear_requests(
            mock=respx_mock,
            page_id=parent_page_id,
        )
        == clears_before
    )


def test_upload_without_page_id_or_parent(
    *,
    tmp_path: Path,
) -> None:
    """Title matching requires a parent page or database."""
    blocks_file = _write_blocks_file(tmp_path=tmp_path, block_dicts=[])

    result = _invoke_upload(
        blocks_file=blocks_file,
        parent_page_id=None,
        mock_api_base_url="https://example.invalid",
    )

    usage_error_exit_code = 2
    assert result.exit_code == usage_error_exit_code
    assert "exactly 1 of the following parameters must be set" in result.output


def test_upload_page_not_found_error(
    *,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    mock_api_base_url: str,
    notion_token: str,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """A useful error is shown when no page with the given ID exists."""
    # The missing page triggers WARNING logs from ``notion_client`` and
    # ``ultimate_notion``. With ``log_cli`` enabled, the live-log handler in
    # ``pytest`` suspends and resumes global capture for WARNING records,
    # which replaces ``sys.stderr`` mid-invocation and breaks the stream
    # capture of ``CliRunner``.  Silence the loggers so ``result.output``
    # stays intact.  ``notion_client`` resets its own logger level on every
    # client construction, so disable it rather than lowering its level.
    monkeypatch.setattr(
        target=logging.getLogger(name="notion_client"),
        name="disabled",
        value=True,
    )
    caplog.set_level(level=logging.ERROR, logger="ultimate_notion.session")
    assert notion_token
    blocks_file = _write_blocks_file(
        tmp_path=tmp_path,
        block_dicts=_paragraph_blocks(
            text_content="Hello from WireMock upload test",
        ),
    )

    result = _invoke_upload(
        blocks_file=blocks_file,
        parent_page_id=parent_page_id,
        mock_api_base_url=mock_api_base_url,
        page_id="40400000-0000-0000-0000-000000000404",
    )

    assert result.exit_code == 1
    assert (
        "No page found with ID '40400000-0000-0000-0000-000000000404'."
        in result.output
    )


def test_upload_ambiguous_title_error(
    *,
    mock_api_base_url: str,
    notion_token: str,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """The CLI explains how to resolve an ambiguous page title."""
    assert notion_token
    blocks_file = _write_blocks_file(tmp_path=tmp_path, block_dicts=[])
    message = (
        "Found 2 pages matching title 'Upload Title'. "
        "Use --page-id to select the page to update."
    )

    with patch(
        target="_notion_scripts.upload.upload_to_notion",
        side_effect=PageTitleAmbiguousError(message),
    ):
        result = _invoke_upload(
            blocks_file=blocks_file,
            parent_page_id=parent_page_id,
            mock_api_base_url=mock_api_base_url,
        )

    assert result.exit_code == 1
    assert result.output == f"Error: {message}\n"
