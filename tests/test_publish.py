"""Tests for the _publish_to_notion event callback."""

import json
import textwrap
from collections.abc import Callable
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
import requests
import respx
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import BulletedItem
from ultimate_notion.rich_text import text
from ultimate_notion.utils import serialize_block_with_children

from sphinx_notion._upload import PageHasSubpagesError
from tests._wiremock import (
    JSONValue,
    count_mock_requests,
    count_page_metadata_clear_requests,
    json_array,
    json_object,
)


def test_publish_skips_on_exception(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion returns immediately when a build exception is
    given.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(
        srcdir=srcdir,
        confoverrides={"extensions": ["sphinx_notion"]},
    )
    warnings_before = app.warning.getvalue()
    _ = app.emit("build-finished", RuntimeError("build failed"))
    assert app.warning.getvalue() == warnings_before


def test_publish_skips_when_disabled(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion returns immediately when notion_publish is False."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    _ = (srcdir / "index.rst").write_text(
        data="Test\n====\n", encoding="utf-8"
    )
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": False,
        },
    )
    app.build()
    assert app.statuscode == 0
    assert app.config["notion_notification_mode"] == "default"


def test_publish_rejects_unsupported_notification_mode(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Publishing requires a supported notification mode."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()

    with pytest.raises(
        expected_exception=ExtensionError,
        match="notion_notification_mode must be one of default",
    ):
        _ = make_app(
            srcdir=srcdir,
            confoverrides={
                "extensions": ["sphinx_notion"],
                "notion_publish": True,
                "notion_page_id": "abc123",
                "notion_page_title": "Test Page",
                "notion_notification_mode": "silent",
            },
        )


def test_publish_skips_when_not_notion_builder(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion returns when the active builder is not
    notion.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    _ = (srcdir / "index.rst").write_text(
        data="Test\n====\n", encoding="utf-8"
    )
    app = make_app(
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": "abc123",
            "notion_page_title": "Test",
        },
    )
    app.build()
    assert app.statuscode == 0


def test_publish_skips_when_no_output_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """_publish_to_notion warns and returns when ``index.json`` does not
    exist.
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": "abc123",
            "notion_page_title": "Test",
        },
    )
    _ = app.emit("build-finished", None)
    assert "index.json found" in app.warning.getvalue()


def test_publish_success(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    respx_mock: respx.MockRouter,
    notion_token: str,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """A Notion build with notion_publish=True uploads to the mock Notion
    API.
    """
    del notion_token
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    _ = (srcdir / "index.rst").write_text(
        data="Hello from publish test.\n",
        encoding="utf-8",
    )
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": parent_page_id,
            "notion_page_id": parent_page_id,
            "notion_page_title": "Upload Title",
            "notion_api_base_url": mock_api_base_url,
            "notion_notification_mode": "default",
        },
    )
    append_url_path = f"/v1/blocks/{parent_page_id}/children"
    before_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path=append_url_path,
    )
    metadata_clears_before = count_page_metadata_clear_requests(
        mock=respx_mock,
        page_id=parent_page_id,
    )
    app.build()
    assert app.statuscode == 0
    assert (
        count_mock_requests(
            mock=respx_mock,
            method="PATCH",
            url_path=append_url_path,
        )
        == before_count + 1
    )
    assert (
        count_page_metadata_clear_requests(
            mock=respx_mock,
            page_id=parent_page_id,
        )
        == metadata_clears_before
    )


@pytest.fixture(name="html_publish_page_id")
def fixture_html_publish_page_id(
    *,
    mock_api_base_url: str,
    parent_page_id: str,
    respx_mock: respx.MockRouter,
) -> str:
    """Reuse the page metadata stubs with a separate page ID for HTML."""
    pages_url = f"{mock_api_base_url}/v1/pages"
    decoded: object = httpx.get(url=f"{pages_url}/{parent_page_id}").json()
    page = json_object(value=decoded)
    page_id = "11440000-0000-0000-0000-000000000001"
    page["id"] = page_id
    _ = respx_mock.get(url=f"{pages_url}/{page_id}").respond(json=page)
    _ = respx_mock.patch(
        url=f"{pages_url}/{page_id.replace('-', '')}"
    ).respond(json=page)
    return page_id


def _block_list(*blocks: dict[str, JSONValue]) -> dict[str, JSONValue]:
    """Build a Notion block list response."""
    return {
        "object": "list",
        "type": "block",
        "block": {},
        "results": list(blocks),
        "has_more": False,
        "next_cursor": None,
    }


def _embed_block(*, block_id: str, url: str) -> dict[str, JSONValue]:
    """Build the Notion response for an embed block."""
    return {
        "object": "block",
        "type": "embed",
        "id": block_id,
        "embed": {"url": url},
    }


def _appended_blocks(*, route: respx.Route) -> list[dict[str, JSONValue]]:
    """Read the blocks sent in the latest append request."""
    decoded: object = json.loads(s=route.calls.last.request.content)
    body = json_object(value=decoded)
    return [
        json_object(value=block)
        for block in json_array(value=body["children"])
    ]


def test_publish_nested_html_and_reuse_unchanged_upload(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    html_publish_page_id: str,
    respx_mock: respx.MockRouter,
    notion_token: str,
    tmp_path: Path,
) -> None:
    """Upload nested HTML once and reuse it after its signed URL
    changes.
    """
    del notion_token
    iframe_url = "https://example.com/frame"
    html = b"<p>Interactive artifact</p>"
    guide = tmp_path / "guide"
    guide.mkdir()
    (tmp_path / "conf.py").touch()
    _ = (guide / "index.rst").write_text(
        data=textwrap.dedent(
            text=f"""\
                * Item with HTML

                  .. notion-html:: chart file.htm

                .. iframe:: {iframe_url}
                """
        ),
        encoding="utf-8",
    )
    _ = (guide / "chart file.htm").write_bytes(data=html)

    item_id = "11440000-0000-0000-0000-000000000002"
    item = json_object(
        value=serialize_block_with_children(
            block=BulletedItem(text=text(text="Item with HTML"))
        )
    )
    item.update(id=item_id, has_children=True)
    iframe = _embed_block(
        block_id="11440000-0000-0000-0000-000000000003", url=iframe_url
    )
    signed_url = (
        "https://prod-files-secure.s3.us-west-2.amazonaws.com/chart%20file.htm"
        "?X-Amz-Signature="
    )
    html_block_id = "11440000-0000-0000-0000-000000000004"
    uploaded_html = _embed_block(
        block_id=html_block_id, url=f"{signed_url}original"
    )
    blocks_url = f"{mock_api_base_url}/v1/blocks"
    page_children = f"{blocks_url}/{html_publish_page_id}/children"
    item_children = f"{blocks_url}/{item_id}/children"
    root_listing = respx_mock.get(url=page_children).respond(
        json=_block_list()
    )
    root_append = respx_mock.patch(url=page_children).respond(
        json=_block_list(item, iframe)
    )
    nested_append = respx_mock.patch(url=item_children).respond(
        json=_block_list(uploaded_html)
    )
    uploads_before = count_mock_requests(
        mock=respx_mock, method="POST", url_path="/v1/file_uploads"
    )
    app = make_app(
        srcdir=tmp_path,
        buildername="notion",
        confoverrides={
            "extensions": ["sphinx_notion", "sphinx_iframes"],
            "root_doc": "guide/index",
            "notion_publish": True,
            "notion_page_id": html_publish_page_id,
            "notion_page_title": "Upload Title",
            "notion_api_base_url": mock_api_base_url,
        },
    )

    app.build()

    assert app.statuscode == 0
    appended_item, appended_iframe = _appended_blocks(route=root_append)
    assert appended_item["type"] == "bulleted_list_item"
    assert appended_iframe["embed"] == {"url": iframe_url, "caption": []}
    (appended_html,) = _appended_blocks(route=nested_append)
    assert appended_html["embed"] == {
        "type": "file_upload",
        "file_upload": {"id": "ff000000-0000-0000-0000-000000000001"},
        "caption": [],
    }

    refreshed_url = f"{signed_url}refreshed"
    _ = root_listing.respond(json=_block_list(item, iframe))
    _ = respx_mock.get(url=item_children).respond(
        json=_block_list(
            _embed_block(block_id=html_block_id, url=refreshed_url)
        )
    )
    response = requests.Response()
    response.status_code = HTTPStatus.OK
    response.raw = BytesIO(initial_bytes=html)
    with patch.object(
        target=requests, attribute="get", return_value=response
    ) as download:
        app.build(force_all=True)

    assert app.statuscode == 0
    download.assert_called_once_with(
        url=refreshed_url, stream=True, timeout=10
    )
    assert root_append.call_count == 1
    assert nested_append.call_count == 1
    assert (
        count_mock_requests(
            mock=respx_mock, method="POST", url_path="/v1/file_uploads"
        )
        == uploads_before + 1
    )


def test_publish_toctree_as_page_hierarchy(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Each reachable document is published under its parent."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    _ = (srcdir / "index.rst").write_text(
        data="Root\n====\n\n.. toctree::\n\n   detail\n   guide\n",
        encoding="utf-8",
    )
    _ = (srcdir / "guide.rst").write_text(
        data="Guide\n=====\n\n.. toctree::\n\n   detail\n",
        encoding="utf-8",
    )
    _ = (srcdir / "detail.rst").write_text(
        data="Detail\n======\n",
        encoding="utf-8",
    )
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_page_id": "root-page-id",
            "notion_page_title": "Documentation",
        },
    )
    pages = [
        SimpleNamespace(id="root-id", url="https://notion.test/root"),
        SimpleNamespace(id="guide-id", url="https://notion.test/guide"),
        SimpleNamespace(id="detail-id", url="https://notion.test/detail"),
    ]

    with (
        patch(target="sphinx_notion.Session"),
        patch(
            target="sphinx_notion.upload_to_notion",
            side_effect=[
                *pages,
                pages[0],
                pages[2],
                pages[1],
                pages[0],
            ],
        ) as upload,
    ):
        app.build()
        assert app.statuscode == 0
        assert upload.call_count == len(pages)
        assert upload.call_args_list[0].kwargs["page_id"] == "root-page-id"
        assert upload.call_args_list[0].kwargs["allow_subpages"] is True
        assert upload.call_args_list[1].kwargs["parent_page_id"] == "root-id"
        assert upload.call_args_list[1].kwargs["title"] == "Guide"
        assert upload.call_args_list[1].kwargs["allow_subpages"] is True
        assert upload.call_args_list[2].kwargs["parent_page_id"] == "guide-id"
        assert upload.call_args_list[2].kwargs["title"] == "Detail"
        assert upload.call_args_list[2].kwargs["allow_subpages"] is False

        upload.reset_mock()
        app.env.toctree_includes["detail"] = ["guide", "index"]
        _ = app.emit("build-finished", None)

        assert upload.call_count == len(pages)
        assert upload.call_args_list[1].kwargs["parent_page_id"] == "root-id"
        assert upload.call_args_list[1].kwargs["title"] == "Detail"
        assert upload.call_args_list[2].kwargs["parent_page_id"] == "detail-id"
        assert upload.call_args_list[2].kwargs["title"] == "Guide"

        upload.reset_mock()
        app.env.toctree_includes["detail"] = list[str]()
        app.env.toctree_includes["index"].append("guide")
        (Path(app.outdir) / "guide.json").unlink()
        _ = app.emit("build-finished", None)

        assert upload.call_count == 1
        assert "No guide.json found" in app.warning.getvalue()


def test_publish_replace_strategy(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    respx_mock: respx.MockRouter,
    notion_token: str,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """Automatic publishing passes its configured replace strategy."""
    del notion_token
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    _ = (srcdir / "index.rst").write_text(
        data="Hello from WireMock upload test\n",
        encoding="utf-8",
    )
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": parent_page_id,
            "notion_page_title": "Upload Title",
            "notion_api_base_url": mock_api_base_url,
            "notion_upload_strategy": "replace",
        },
    )
    append_url_path = f"/v1/blocks/{parent_page_id}/children"
    delete_url_path = "/v1/blocks/c02fc1d3-db8b-45c5-a222-27595b15aea7"
    before_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path=append_url_path,
    )
    before_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path=delete_url_path,
    )

    app.build()

    assert app.statuscode == 0
    assert app.config["notion_upload_strategy"] == "replace"
    assert (
        count_mock_requests(
            mock=respx_mock,
            method="PATCH",
            url_path=append_url_path,
        )
        == before_append_count + 1
    )
    assert (
        count_mock_requests(
            mock=respx_mock,
            method="DELETE",
            url_path=delete_url_path,
        )
        == before_delete_count + 1
    )


def test_publish_propagates_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    notion_token: str,
    tmp_path: Path,
) -> None:
    """A Notion build with a failing upload propagates the error."""
    del notion_token
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").touch()
    _ = (srcdir / "index.rst").write_text(data="", encoding="utf-8")
    app = make_app(
        buildername="notion",
        srcdir=srcdir,
        confoverrides={
            "extensions": ["sphinx_notion"],
            "notion_publish": True,
            "notion_parent_page_id": "aaaa0000-0000-0000-0000-000000000001",
            "notion_page_title": "Upload Title",
            "notion_api_base_url": mock_api_base_url,
        },
    )
    with pytest.raises(expected_exception=ExtensionError) as exc_info:
        app.build()
    assert isinstance(exc_info.value.__cause__, PageHasSubpagesError)
