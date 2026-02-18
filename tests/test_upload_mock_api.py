"""Opt-in integration test for upload synchronization against a mock
API.
"""

import os
from pathlib import Path

import pytest
import requests
from ultimate_notion import ExternalFile, Session
from ultimate_notion.blocks import (
    BulletedItem,
    Divider,
)
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.obj_api.objects import UploadedFile as UnoUploadedFile
from ultimate_notion.rich_text import text

import sphinx_notion._upload as notion_upload
from sphinx_notion._upload import (
    DiscussionsExistError,
    PageHasDatabasesError,
    PageHasSubpagesError,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_TESTS") == "1",
    reason="SKIP_DOCKER_TESTS is set",
)


def _count_wiremock_requests(
    *,
    base_url: str,
    method: str,
    url_path: str,
) -> int:
    """Count matching requests captured by WireMock."""
    payload = {
        "method": method,
        "urlPath": url_path,
    }

    response = requests.post(
        url=f"{base_url}/__admin/requests/count",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    count = response.json()["count"]
    assert isinstance(count, int)
    return count


def _file_upload_create_count(*, base_url: str) -> int:
    """Count calls to file-upload creation endpoint."""
    return _count_wiremock_requests(
        base_url=base_url,
        method="POST",
        url_path="/v1/file_uploads",
    )


def test_upload_to_notion_with_wiremock(
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """It is possible to upload a page with the mock API."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
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


def test_upload_deletes_and_replaces_changed_blocks(
    mock_api_base_url: str,
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """Changed content triggers block deletion and re-upload."""
    before_delete_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="DELETE",
        url_path="/v1/blocks/c02fc1d3-db8b-45c5-a222-27595b15aea7",
    )
    before_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path=f"/v1/blocks/{parent_page_id}/children",
    )
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Different content triggers sync"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=True,
    )
    after_delete_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="DELETE",
        url_path="/v1/blocks/c02fc1d3-db8b-45c5-a222-27595b15aea7",
    )
    after_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path=f"/v1/blocks/{parent_page_id}/children",
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert after_delete_count == before_delete_count + 1
    assert after_append_count == before_append_count + 1


def test_upload_with_icon(
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """It is possible to upload a page with an emoji icon."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
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
    notion_session: Session,
    parent_page_id: str,
) -> None:
    """It is possible to upload a page with a cover URL."""
    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from WireMock upload test"))
        ],
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
            parent_page_id="cccc0000-0000-0000-0000-000000000001",
            parent_database_id=None,
            title="Upload Title",
            icon=None,
            cover_path=None,
            cover_url=None,
            cancel_on_discussion=True,
        )


def test_upload_with_database_parent(
    notion_session: Session,
    mock_api_base_url: str,
) -> None:
    """It is possible to upload a page to a database."""
    parent_database_id = "db000000-0000-0000-0000-000000000001"
    query_url_path = f"/v1/databases/{parent_database_id}/query"

    before_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="POST",
        url_path=query_url_path,
    )

    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        parent_page_id=None,
        parent_database_id=parent_database_id,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )

    after_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="POST",
        url_path=query_url_path,
    )

    assert page.title == "Upload Title"
    assert after_count == before_count + 1


def test_upload_with_cover_path(
    mock_api_base_url: str,
    notion_session: Session,
    parent_page_id: str,
    tmp_path: Path,
) -> None:
    """It is possible to upload a page with a local cover file."""
    cover_file = tmp_path / "cover.png"
    cover_file.write_bytes(data=b"fake-png-data")
    before_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
    )

    page = notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoParagraph(text=text(text="Hello from Microcks upload test"))
        ],
        parent_page_id=parent_page_id,
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=cover_file,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
    )

    assert page.title == "Upload Title"
    assert str(object=page.id) == parent_page_id
    assert isinstance(page.cover, ExternalFile)
    assert page.cover.url == "https://example.com/cover.png"
    assert after_upload_count == before_upload_count + 1


def test_upload_with_file_block(
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


def test_upload_with_nested_file_block(
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
    mock_api_base_url: str,
    notion_session: Session,
) -> None:
    """Prefix and suffix matching skips unchanged blocks."""
    before_delete_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="DELETE",
        url_path="/v1/blocks/dddd0000-0000-0000-0000-000000000011",
    )
    before_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
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
        parent_page_id="dddd0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_delete_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="DELETE",
        url_path="/v1/blocks/dddd0000-0000-0000-0000-000000000011",
    )
    after_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path="/v1/blocks/dddd0000-0000-0000-0000-000000000002/children",
    )

    assert after_delete_count == before_delete_count + 1
    assert after_append_count == before_append_count + 1


def test_upload_file_block_name_mismatch(
    notion_session: Session,
    mock_api_base_url: str,
    tmp_path: Path,
) -> None:
    """File block with name mismatch triggers re-upload."""
    img_file = tmp_path / "different.png"
    img_file.write_bytes(data=b"image-data")

    before_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
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
        parent_page_id="eeee0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
    )

    assert after_upload_count == before_upload_count + 1


def test_upload_file_block_caption_mismatch(
    notion_session: Session,
    mock_api_base_url: str,
    tmp_path: Path,
) -> None:
    """File block with caption mismatch triggers re-upload."""
    img_file = tmp_path / "test.png"
    img_file.write_bytes(data=b"image-data")

    before_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoImage(
                file=ExternalFile(url=img_file.as_uri()),
                caption="new caption",
            ),
        ],
        parent_page_id="eeee0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
    )

    assert after_upload_count == before_upload_count + 1


def test_upload_file_block_external_url(
    notion_session: Session,
    mock_api_base_url: str,
) -> None:
    """File block with external URL skips upload and compares directly."""
    before_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
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
        parent_page_id="eeee0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
    )

    assert after_upload_count == before_upload_count


def test_upload_file_block_existing_is_external(
    notion_session: Session,
    mock_api_base_url: str,
    tmp_path: Path,
) -> None:
    """File block with existing ExternalFile triggers re-upload."""
    img_file = tmp_path / "test.png"
    img_file.write_bytes(data=b"image-data")

    before_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[
            UnoImage(file=ExternalFile(url=img_file.as_uri())),
        ],
        parent_page_id="ffff0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_upload_count = _file_upload_create_count(
        base_url=mock_api_base_url,
    )

    assert after_upload_count == before_upload_count + 1


def test_upload_matching_parent_blocks(
    mock_api_base_url: str,
    notion_session: Session,
) -> None:
    """Matching parent blocks with children are not re-uploaded."""
    local_block = BulletedItem(text=text(text="item"))
    local_block.append(blocks=[Divider()])

    before_delete_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="DELETE",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000010",
    )
    before_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000002/children",
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[local_block],
        parent_page_id="aabb0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_delete_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="DELETE",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000010",
    )
    after_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000002/children",
    )

    assert after_delete_count == before_delete_count
    assert after_append_count == before_append_count


def test_upload_parent_block_different_children_count(
    mock_api_base_url: str,
    notion_session: Session,
) -> None:
    """Parent block with different children count triggers re-upload."""
    local_block = BulletedItem(text=text(text="item"))
    local_block.append(blocks=[Divider(), Divider()])

    before_delete_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="DELETE",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000010",
    )
    before_parent_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000002/children",
    )
    before_child_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000020/children",
    )
    notion_upload.upload_to_notion(
        session=notion_session,
        blocks=[local_block],
        parent_page_id="aabb0000-0000-0000-0000-000000000001",
        parent_database_id=None,
        title="Upload Title",
        icon=None,
        cover_path=None,
        cover_url=None,
        cancel_on_discussion=False,
    )
    after_delete_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="DELETE",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000010",
    )
    after_parent_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000002/children",
    )
    after_child_append_count = _count_wiremock_requests(
        base_url=mock_api_base_url,
        method="PATCH",
        url_path="/v1/blocks/aabb0000-0000-0000-0000-000000000020/children",
    )

    assert after_delete_count == before_delete_count + 1
    assert after_parent_append_count == before_parent_append_count + 1
    assert after_child_append_count == before_child_append_count + 1
