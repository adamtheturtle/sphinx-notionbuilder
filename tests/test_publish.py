"""Tests for the _publish_to_notion event callback."""

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
import requests
import respx
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import BulletedItem
from ultimate_notion.rich_text import text

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


def _block_list(*, blocks: Sequence[object]) -> dict[str, object]:
    """Build the response envelope for the Notion block list endpoint."""
    return {
        "object": "list",
        "type": "block",
        "block": {},
        "results": list(blocks),
        "has_more": False,
        "next_cursor": None,
    }


def _appended_block(*, route: respx.Route, index: int) -> dict[str, JSONValue]:
    """Extract a block from an append request."""
    decoded: object = json.loads(s=route.calls.last.request.content)
    body = json_object(value=decoded)
    return json_object(value=json_array(value=body["children"])[index])


def test_publish_nested_html_and_reuse_unchanged_upload(
    *,
    make_app: Callable[..., SphinxTestApp],
    mock_api_base_url: str,
    respx_mock: respx.MockRouter,
    notion_token: str,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """Publish HTML by ID and compare the file at the refreshed URL."""
    del notion_token
    srcdir = tmp_path / "src"
    guide = srcdir / "guide"
    guide.mkdir(parents=True)
    (srcdir / "conf.py").touch()
    _ = (guide / "index.rst").write_text(
        data=(
            "* Item with HTML\n\n"
            "  .. notion-html:: chart file.htm\n\n"
            ".. iframe:: https://example.com/frame\n"
        ),
        encoding="utf-8",
    )
    html = b"<p>Interactive artifact</p>"
    _ = (guide / "chart file.htm").write_bytes(data=html)

    page_id = "11440000-0000-0000-0000-000000000001"
    item_id = "11440000-0000-0000-0000-000000000002"
    original_page = httpx.get(
        url=f"{mock_api_base_url}/v1/pages/{parent_page_id}"
    )
    decoded: object = original_page.json()
    page = json_object(value=decoded)
    page["id"] = page_id
    page_url = f"{mock_api_base_url}/v1/pages/{page_id}"
    _ = respx_mock.get(url=page_url).respond(json=page)
    _ = respx_mock.patch(
        url=f"{mock_api_base_url}/v1/pages/{page_id.replace('-', '')}"
    ).respond(json=page)
    children_url = f"{mock_api_base_url}/v1/blocks/{page_id}/children"
    root_children = respx_mock.get(url=children_url).respond(
        json=_block_list(blocks=[])
    )
    nested_url = f"{mock_api_base_url}/v1/blocks/{item_id}/children"
    remote_url = "https://example.com/frame"
    remote = {
        "object": "block",
        "type": "embed",
        "id": "11440000-0000-0000-0000-000000000003",
        "embed": {"url": remote_url},
    }
    signed_url = (
        "https://prod-files-secure.s3.us-west-2.amazonaws.com/chart%20file.htm"
        "?X-Amz-Signature="
    )
    artifact = {
        "object": "block",
        "type": "embed",
        "id": "11440000-0000-0000-0000-000000000004",
        "embed": {"url": f"{signed_url}original"},
    }
    nested_children = respx_mock.get(url=nested_url).respond(
        json=_block_list(blocks=[artifact])
    )
    nested_append = respx_mock.patch(url=nested_url).respond(
        json=_block_list(blocks=[artifact])
    )

    item = json_object(
        value=BulletedItem(
            text=text(text="Item with HTML")
        ).obj_ref.serialize_for_api()
    )
    item.update(id=item_id, has_children=True)
    root_append = respx_mock.patch(url=children_url).respond(
        json=_block_list(blocks=[item, remote])
    )
    app = make_app(
        srcdir=srcdir,
        buildername="notion",
        confoverrides={
            "extensions": ["sphinx_notion", "sphinx_iframes"],
            "root_doc": "guide/index",
            "notion_publish": True,
            "notion_page_id": page_id,
            "notion_page_title": "Upload Title",
            "notion_api_base_url": mock_api_base_url,
        },
    )
    upload_count = count_mock_requests(
        mock=respx_mock, method="POST", url_path="/v1/file_uploads"
    )
    app.build()
    assert app.statuscode == 0
    assert _appended_block(route=root_append, index=1)["embed"] == {
        "url": remote_url,
        "caption": [],
    }
    assert _appended_block(route=nested_append, index=0)["embed"] == {
        "type": "file_upload",
        "file_upload": {"id": "ff000000-0000-0000-0000-000000000001"},
        "caption": [],
    }
    _ = root_children.respond(json=_block_list(blocks=[item, remote]))
    fresh_url = f"{signed_url}refreshed"
    fresh_artifact = {**artifact, "embed": {"url": fresh_url}}
    _ = nested_children.respond(json=_block_list(blocks=[fresh_artifact]))
    response = MagicMock(iter_content=MagicMock(return_value=[html]))
    response.configure_mock(**{"__enter__.return_value": response})
    with patch.object(
        target=requests, attribute="get", return_value=response
    ) as download:
        app.build(force_all=True)
        download.assert_called_once_with(
            url=fresh_url, stream=True, timeout=10
        )

    assert app.statuscode == 0
    assert root_append.call_count == 1
    assert nested_append.call_count == 1
    assert (
        count_mock_requests(
            mock=respx_mock, method="POST", url_path="/v1/file_uploads"
        )
        == upload_count + 1
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
