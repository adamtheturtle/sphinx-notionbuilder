"""Integration test for upload synchronization against a mock API."""

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import httpx
import pytest
import respx
from notion_client.errors import HTTPResponseError
from ultimate_notion import ExternalFile, Session
from ultimate_notion.blocks import (
    Block,
    BulletedItem,
    Callout,
    ChildrenMixin,
    Divider,
)
from ultimate_notion.blocks import File as UnoFile
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock
from ultimate_notion.obj_api.objects import UploadedFile as UnoUploadedFile
from ultimate_notion.rich_text import text

import sphinx_notion._upload as notion_upload
from sphinx_notion._upload import (
    CloudflareWAFBlockError,
    DiscussionsExistError,
    PageHasDatabasesError,
    PageHasSubpagesError,
    PageNotFoundError,
)
from tests._wiremock import (
    count_mock_requests,
    count_page_metadata_clear_requests,
)

if TYPE_CHECKING:
    from respx.models import Call


def _file_upload_create_count(*, mock: respx.MockRouter) -> int:
    """Count calls to file-upload creation endpoint."""
    return count_mock_requests(
        mock=mock,
        method="POST",
        url_path="/v1/file_uploads",
    )


def _cover_clear_count(*, mock: respx.MockRouter) -> int:
    """Count page updates that explicitly clear the cover."""
    count = 0
    calls: list[Call] = list(mock.calls)
    for call in calls:
        if (
            call.request.method == "PATCH"
            and call.request.url.path.startswith("/v1/pages/")
            and json.loads(s=call.request.content).get("cover", "missing")
            is None
        ):
            count += 1
    return count


def test_count_page_metadata_clear_requests(
    *,
    parent_page_id: str,
    respx_mock: respx.MockRouter,
) -> None:
    """Icon and cover null updates are both recognized as clears."""
    clears_before = count_page_metadata_clear_requests(
        mock=respx_mock,
        page_id=parent_page_id,
    )
    for payload in ({"icon": None}, {"cover": None}):
        response = httpx.patch(
            url=f"https://mock.notion.test/v1/pages/{parent_page_id}",
            json=payload,
        )
        assert response.status_code == httpx.codes.OK

    assert (
        count_page_metadata_clear_requests(
            mock=respx_mock,
            page_id=parent_page_id,
        )
        == clears_before + 2
    )


def test_upload_to_notion_with_wiremock(
    *,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """It is possible to upload a page with the mock API."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
        page_id=None,
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
    assert page.blocks[0].rich_text == "Hello from WireMock upload test"


def test_omitted_page_metadata_is_preserved(
    *,
    notion_session: Session,
    parent_page_id: str,
    respx_mock: respx.MockRouter,
) -> None:
    """Omitted icon and cover values do not clear existing metadata."""
    clears_before = count_page_metadata_clear_requests(
        mock=respx_mock,
        page_id=parent_page_id,
    )
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
        page_id=parent_page_id,
        parent_page_id=None,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.icon == "\N{MEMO}"
    assert isinstance(page.cover, ExternalFile)
    assert page.cover.url == "https://example.com/cover.png"
    assert (
        count_page_metadata_clear_requests(
            mock=respx_mock,
            page_id=parent_page_id,
        )
        == clears_before
    )


def test_upload_deletes_and_replaces_changed_blocks(
    *,
    respx_mock: respx.MockRouter,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """Changed content triggers block deletion and re-upload."""
    before_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/c02fc1d3-db8b-45c5-a222-27595b15aea7",
    )
    before_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path=f"/v1/blocks/{parent_page_id}/children",
    )
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Different content triggers sync"))
        ],
        page_id=None,
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=True,
    )
    after_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/c02fc1d3-db8b-45c5-a222-27595b15aea7",
    )
    after_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path=f"/v1/blocks/{parent_page_id}/children",
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert after_delete_count == before_delete_count + 1
    assert after_append_count == before_append_count + 1


def test_failed_file_upload_leaves_existing_blocks(
    *,
    respx_mock: respx.MockRouter,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """A failing file upload does not delete existing page blocks.

    Regression test: file uploads must happen before any existing blocks
    are deleted, so that a rejected file leaves the live page untouched
    rather than emptied.
    """
    before_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/c02fc1d3-db8b-45c5-a222-27595b15aea7",
    )
    upload_error = RuntimeError("File rejected by Notion")
    with (
        patch.object(
            target=notion_upload,
            attribute="_block_with_uploaded_file",
            side_effect=upload_error,
        ),
        pytest.raises(expected_exception=RuntimeError, match="File rejected"),
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[
                UnoParagraph(text=text(text="Different content triggers sync"))
            ],
            page_id=None,
            parent_page_id=parent_page_id,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )

    after_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/c02fc1d3-db8b-45c5-a222-27595b15aea7",
    )
    assert after_delete_count == before_delete_count


def test_upload_with_icon(
    *,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """It is possible to upload a page with an emoji icon."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
        page_id=None,
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
    assert page.icon == "\N{MEMO}"


def test_upload_with_cover_url(
    *,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """It is possible to upload a page with a cover URL."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
        page_id=None,
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
    assert isinstance(page.cover, ExternalFile)
    assert page.cover.url == "https://example.com/cover.png"


def test_upload_page_has_subpages_error(
    notion_session: Session,
) -> None:
    """PageHasSubpagesError raised when the target page has subpages."""
    with pytest.raises(expected_exception=PageHasSubpagesError):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[],
            page_id=None,
            parent_page_id="aaaa0000-0000-0000-0000-000000000001",
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_upload_page_has_databases_error(
    notion_session: Session,
) -> None:
    """PageHasDatabasesError raised when the target page has databases."""
    with pytest.raises(expected_exception=PageHasDatabasesError):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[],
            page_id=None,
            parent_page_id="bbbb0000-0000-0000-0000-000000000001",
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_upload_discussions_exist_error(
    notion_session: Session,
) -> None:
    """DiscussionsExistError raised when blocks to delete have discussions."""
    with pytest.raises(
        expected_exception=DiscussionsExistError,
        match=r"1 block.*1 discussion",
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[
                UnoParagraph(
                    text=text(text="Different content triggers sync"),
                ),
            ],
            page_id=None,
            parent_page_id="cccc0000-0000-0000-0000-000000000001",
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=True,
        )


def test_upload_with_page_id(
    *,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """A page given by ID is updated and renamed to the given title."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
        page_id=parent_page_id,
        parent_page_id=None,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert len(page.blocks) == 1
    assert isinstance(page.blocks[0], UnoParagraph)
    assert page.blocks[0].rich_text == "Hello from WireMock upload test"


def test_upload_page_not_found_error(
    *,
    notion_session: Session,
) -> None:
    """PageNotFoundError raised when no page with the given ID exists."""
    missing_page_id = "40400000-0000-0000-0000-000000000404"
    with pytest.raises(
        expected_exception=PageNotFoundError,
        match=f"No page found with ID '{missing_page_id}'.",
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[
                UnoParagraph(
                    text=text(text="Hello from WireMock upload test"),
                ),
            ],
            page_id=missing_page_id,
            parent_page_id=None,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_upload_with_database_parent(
    *,
    notion_session: Session,
    respx_mock: respx.MockRouter,
) -> None:
    """It is possible to upload a page to a database."""
    parent_database_id = "d5000000-0000-0000-0000-000000000001"
    query_url_path = f"/v1/data_sources/{parent_database_id}/query"

    before_count = count_mock_requests(
        mock=respx_mock,
        method="POST",
        url_path=query_url_path,
    )

    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        page_id=None,
        parent_page_id=None,
        parent_database_id=parent_database_id,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    after_count = count_mock_requests(
        mock=respx_mock,
        method="POST",
        url_path=query_url_path,
    )

    assert page.title == "Upload Title"
    assert after_count == before_count + 1


def test_upload_with_cover_path(
    *,
    respx_mock: respx.MockRouter,
    notion_session: Session,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """It is possible to upload a page with a local cover file."""
    cover_file = tmp_path / "cover.png"
    cover_file.write_bytes(data=b"fake-png-data")
    before_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )

    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        page_id=None,
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=cover_file,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert isinstance(page.cover, ExternalFile)
    assert page.cover.url == "https://example.com/cover.png"
    assert after_upload_count == before_upload_count + 1


def test_upload_with_unchanged_cover_path(
    *,
    respx_mock: respx.MockRouter,
    notion_session: Session,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """An unchanged local cover is neither uploaded nor cleared."""
    cover_file = tmp_path / "cover.png"
    cover_file.write_bytes(data=b"unchanged-cover")
    before_clear_count = _cover_clear_count(mock=respx_mock)
    before_upload_count = _file_upload_create_count(mock=respx_mock)

    with patch.object(
        target=notion_upload,
        attribute="_get_uploaded_cover",
        return_value=None,
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[
                UnoParagraph(text=text(text="Hello from Microcks upload test"))
            ],
            page_id=None,
            parent_page_id=parent_page_id,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=cover_file,
            cover_url=None,
            cancel_on_discussion=False,
        )

    assert _cover_clear_count(mock=respx_mock) == before_clear_count
    assert _file_upload_create_count(mock=respx_mock) == before_upload_count


def test_upload_with_file_block(
    *,
    notion_session: Session,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """It is possible to upload a page with a file:// image block."""
    img_file = tmp_path / "test.png"
    img_file.write_bytes(data=b"fake-image-data")

    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoImage(file=ExternalFile(url=img_file.as_uri())),
        ],
        page_id=None,
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert len(page.blocks) == 1
    uploaded_image_block = page.blocks[0]
    assert isinstance(uploaded_image_block, UnoImage)
    assert str(object=uploaded_image_block.id) == (
        "30f89f8f-57ff-4f6c-a13d-4720d0d4f123"
    )
    uploaded_image = uploaded_image_block.obj_ref.image
    assert uploaded_image is not None
    assert isinstance(uploaded_image, UnoUploadedFile)
    uploaded_image_file = uploaded_image.file_upload
    assert str(object=uploaded_image_file.id) == (
        "ff000000-0000-0000-0000-000000000001"
    )


def test_upload_local_file_preserves_name_and_caption(
    *,
    notion_session: Session,
    parent_page_id: str,
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """A local file's custom presentation survives file upload."""
    local_file = tmp_path / "archive.zip"
    local_file.write_bytes(data=b"release-bundle")
    append_url_path = f"/v1/blocks/{parent_page_id}/children"
    appends_before = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path=append_url_path,
    )

    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoFile(
                file=ExternalFile(url=local_file.as_uri()),
                name="Download the release bundle",
                caption="Current release",
            )
        ],
        page_id=None,
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    calls: list[Call] = list(respx_mock.calls)
    append_calls = [
        call
        for call in calls
        if call.request.method == "PATCH"
        and call.request.url.path == append_url_path
    ]
    assert len(append_calls) == appends_before + 1
    payload = json.loads(s=append_calls[-1].request.content)
    uploaded_file = payload["children"][0]["file"]
    assert uploaded_file["name"] == "Download the release bundle"
    assert uploaded_file["caption"][0]["text"]["content"] == "Current release"


def test_upload_with_nested_file_block(
    *,
    notion_session: Session,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """Upload with a parent block containing a file child block."""
    img_file = tmp_path / "nested.png"
    img_file.write_bytes(data=b"fake-nested-image-data")

    parent_block = BulletedItem(text=text(text="Item with image"))
    parent_block.append(
        blocks=[UnoImage(file=ExternalFile(url=img_file.as_uri()))],
    )

    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[parent_block],
        page_id=None,
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert len(page.blocks) == 1
    uploaded_parent_block = page.blocks[0]
    assert isinstance(uploaded_parent_block, BulletedItem)
    assert len(uploaded_parent_block.children) == 1
    uploaded_child_block = uploaded_parent_block.children[0]
    assert isinstance(uploaded_child_block, UnoImage)
    uploaded_child_image = uploaded_child_block.obj_ref.image
    assert uploaded_child_image is not None
    assert isinstance(uploaded_child_image, UnoUploadedFile)
    uploaded_child_file = uploaded_child_image.file_upload
    assert str(object=uploaded_child_file.id) == (
        "ff000000-0000-0000-0000-000000000001"
    )


def test_upload_prefix_suffix_matching(
    *,
    respx_mock: respx.MockRouter,
    notion_session: Session,
) -> None:
    """Prefix and suffix matching skips unchanged blocks."""
    before_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/dddd0000-0000-0000-0000-000000000011",
    )
    before_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path="/v1/blocks/dddd0000-0000-0000-0000-000000000002/children",
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="same")),
            UnoParagraph(text=text(text="new")),
            Divider(),
        ],
        page_id=None,
        parent_page_id="dddd0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/dddd0000-0000-0000-0000-000000000011",
    )
    after_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path="/v1/blocks/dddd0000-0000-0000-0000-000000000002/children",
    )

    assert after_delete_count == before_delete_count + 1
    assert after_append_count == before_append_count + 1


def test_upload_file_block_name_mismatch(
    *,
    notion_session: Session,
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """File block with name mismatch triggers re-upload."""
    img_file = tmp_path / "different.png"
    img_file.write_bytes(data=b"image-data")

    before_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoImage(
                file=ExternalFile(
                    url=img_file.as_uri(),
                    name="different.png",
                ),
            ),
        ],
        page_id=None,
        parent_page_id="eeee0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )

    assert after_upload_count == before_upload_count + 1


def test_upload_file_block_caption_mismatch(
    *,
    notion_session: Session,
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """File block with caption mismatch triggers re-upload."""
    img_file = tmp_path / "test.png"
    img_file.write_bytes(data=b"image-data")

    before_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoImage(
                file=ExternalFile(url=img_file.as_uri()),
                caption="new caption",
            ),
        ],
        page_id=None,
        parent_page_id="eeee0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )

    assert after_upload_count == before_upload_count + 1


def test_upload_file_block_external_url(
    *,
    notion_session: Session,
    respx_mock: respx.MockRouter,
) -> None:
    """File block with external URL skips upload and compares directly."""
    before_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoImage(
                file=ExternalFile(
                    url="https://example.com/different.png",
                ),
            ),
        ],
        page_id=None,
        parent_page_id="eeee0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )

    assert after_upload_count == before_upload_count


def test_upload_file_block_existing_is_external(
    *,
    notion_session: Session,
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """File block with existing ExternalFile triggers re-upload."""
    img_file = tmp_path / "test.png"
    img_file.write_bytes(data=b"image-data")

    before_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoImage(file=ExternalFile(url=img_file.as_uri())),
        ],
        page_id=None,
        parent_page_id="ffff0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        mock=respx_mock,
    )

    assert after_upload_count == before_upload_count + 1


def test_upload_matching_parent_blocks(
    *,
    respx_mock: respx.MockRouter,
    notion_session: Session,
) -> None:
    """Matching parent blocks with children are not re-uploaded."""
    local_block = BulletedItem(text=text(text="item"))
    local_block.append(blocks=[Divider()])

    before_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000010",
    )
    before_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000002/children",
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[local_block],
        page_id=None,
        parent_page_id="aabb0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000010",
    )
    after_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000002/children",
    )

    assert after_delete_count == before_delete_count
    assert after_append_count == before_append_count


def test_upload_parent_block_different_children_count(
    *,
    respx_mock: respx.MockRouter,
    notion_session: Session,
) -> None:
    """Parent block with different children count triggers re-upload."""
    local_block = BulletedItem(text=text(text="item"))
    local_block.append(blocks=[Divider(), Divider()])

    before_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000010",
    )
    before_parent_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000002/children",
    )
    before_child_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000020/children",
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[local_block],
        page_id=None,
        parent_page_id="aabb0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_delete_count = count_mock_requests(
        mock=respx_mock,
        method="DELETE",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000010",
    )
    after_parent_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000002/children",
    )
    after_child_append_count = count_mock_requests(
        mock=respx_mock,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000020/children",
    )

    assert after_delete_count == before_delete_count + 1
    assert after_parent_append_count == before_parent_append_count + 1
    assert after_child_append_count == before_child_append_count + 1


def _make_html_http_error(*, status_code: int) -> HTTPResponseError:
    """Create an HTTPResponseError with an HTML response body."""
    return HTTPResponseError(
        code="cloudflare_waf_block",
        status=status_code,
        message="Error",
        headers=httpx.Headers(
            headers={"content-type": "text/html; charset=utf-8"}
        ),
        raw_body_text="<html><body>Error</body></html>",
    )


def test_cloudflare_waf_block(
    *,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """CloudflareWAFBlockError raised when response content-type is
    text/HTML.
    """
    expected = (
        "Request blocked by Cloudflare WAF before reaching Notion API. "
        "Common triggers: path traversal, SQL keywords, XSS patterns, "
        "JNDI strings. The Notion API did not receive this request."
    )
    with (
        patch.object(
            target=ChildrenMixin,
            attribute="append",
            side_effect=_make_html_http_error(status_code=403),
        ),
        pytest.raises(
            expected_exception=CloudflareWAFBlockError,
            match=f"^{re.escape(pattern=expected)}$",
        ),
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[UnoParagraph(text=text(text="WAF trigger content"))],
            page_id=None,
            parent_page_id=parent_page_id,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_non_html_403_not_wrapped(
    *,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """HTTPResponseError with non-HTML body is re-raised unchanged."""
    json_error = HTTPResponseError(
        code="restricted_resource",
        status=403,
        message="Restricted resource",
        headers=httpx.Headers(headers={"content-type": "application/json"}),
        raw_body_text='{"code": "restricted_resource"}',
    )
    with (
        patch.object(
            target=ChildrenMixin,
            attribute="append",
            side_effect=json_error,
        ),
        pytest.raises(expected_exception=HTTPResponseError),
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[UnoParagraph(text=text(text="Content"))],
            page_id=None,
            parent_page_id=parent_page_id,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_non_403_html_not_wrapped(
    *,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """HTTPResponseError with HTML body but non-403 status is re-
    raised.
    """
    with (
        patch.object(
            target=ChildrenMixin,
            attribute="append",
            side_effect=_make_html_http_error(status_code=502),
        ),
        pytest.raises(expected_exception=HTTPResponseError),
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[UnoParagraph(text=text(text="Content"))],
            page_id=None,
            parent_page_id=parent_page_id,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )


def test_file_upload_waf_block_logs_body(
    *,
    notion_session: Session,
    parent_page_id: str,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A WAF-blocked file upload raises CloudflareWAFBlockError and logs
    the response body so the cause can be diagnosed.
    """
    img_file = tmp_path / "diagram.svg"
    img_file.write_bytes(data=b"<svg>CREATE TABLE x (y VARCHAR(255))</svg>")

    waf_body = "<!DOCTYPE html><html>Sorry, you have been blocked</html>"
    waf_error = HTTPResponseError(
        code="cloudflare_waf_block",
        status=403,
        message="Blocked",
        headers=httpx.Headers(
            headers={"content-type": "text/html", "cf-ray": "abc123-LHR"}
        ),
        raw_body_text=waf_body,
    )
    with (
        patch.object(
            target=notion_session,
            attribute="upload",
            side_effect=waf_error,
        ),
        pytest.raises(expected_exception=CloudflareWAFBlockError),
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[UnoImage(file=ExternalFile(url=img_file.as_uri()))],
            page_id=None,
            parent_page_id=parent_page_id,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )

    (record,) = caplog.records
    assert record.getMessage() == (
        "Notion upload of 'diagram.svg' was blocked by the Cloudflare WAF "
        "(HTTP 403, Cloudflare Ray ID: abc123-LHR). The file never reached "
        "Notion. This is typically triggered by literal SQL or script text "
        "in the uploaded bytes -- for example an SVG whose <text> contains "
        "'CREATE TABLE ...'. Rasterize such diagrams to PNG to avoid the "
        f"signature. Response body:\n{waf_body}"
    )


def test_file_upload_other_http_error_logs_body(
    *,
    notion_session: Session,
    parent_page_id: str,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A non-WAF file-upload failure is re-raised unchanged but its
    response body is still logged.
    """
    img_file = tmp_path / "photo.png"
    img_file.write_bytes(data=b"fake-image-data")

    body = '{"code": "validation_error", "message": "too large"}'
    http_error = HTTPResponseError(
        code="validation_error",
        status=400,
        message="too large",
        headers=httpx.Headers(headers={"content-type": "application/json"}),
        raw_body_text=body,
    )
    with (
        patch.object(
            target=notion_session,
            attribute="upload",
            side_effect=http_error,
        ),
        pytest.raises(expected_exception=HTTPResponseError),
    ):
        notion_upload.upload_to_notion(
            session=notion_session,
            blocks=[UnoImage(file=ExternalFile(url=img_file.as_uri()))],
            page_id=None,
            parent_page_id=parent_page_id,
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=False,
        )

    (record,) = caplog.records
    assert record.getMessage() == (
        "Notion upload of 'photo.png' failed: HTTP 400. "
        f"Response body:\n{body}"
    )


def _nested_callout_dict(*, depth: int) -> dict[str, object]:
    """A callout dict nested ``depth`` levels deep, as produced by the
    builder.
    """
    callout = Callout(text=text(text=f"Level {depth}"))
    serialized = callout.obj_ref.serialize_for_api()
    if depth > 1:
        child = _nested_callout_dict(depth=depth - 1)
        callout_body = serialized["callout"]
        assert isinstance(callout_body, dict)
        callout_body["children"] = [child]
    return serialized


def test_deeply_nested_blocks_strip_rejected_fields() -> None:
    """Serializing deeply nested blocks strips fields the Notion API
    rejects at every level of nesting.

    Regression test: each nested callout block retained ``is_archived``
    and ``has_children``, which the API rejects on append.
    """
    block_dict = _nested_callout_dict(depth=3)
    block = Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=block_dict))
    serialized = block.obj_ref.serialize_for_api()
    serialized_text = json.dumps(obj=serialized)
    for field in ("archived", "in_trash", "is_archived", "has_children"):
        assert f'"{field}"' not in serialized_text
