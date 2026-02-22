"""Tests for the upload script."""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result
from pytest_regressions.file_regression import FileRegressionFixture
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

from _notion_scripts.upload import main  # pylint: disable=import-private-name

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_TESTS") == "1",
    reason="SKIP_DOCKER_TESTS is set",
)


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
    parent_page_id: str,
    mock_api_base_url: str,
    cancel_on_discussion: bool = False,
) -> Result:
    """Invoke the upload CLI against the mock Notion API."""
    runner = CliRunner()
    arguments = [
        "--file",
        str(object=blocks_file),
        "--parent-page-id",
        parent_page_id,
        "--title",
        "Upload Title",
        "--notion-api-base-url",
        mock_api_base_url,
    ]
    if cancel_on_discussion:
        arguments.append("--cancel-on-discussion")
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
