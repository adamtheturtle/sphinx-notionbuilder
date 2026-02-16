"""Unit tests for _upload helper functions that don't need a mock API."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

from ultimate_notion import ExternalFile, NotionFile, Session
from ultimate_notion.blocks import (
    Bookmark,
    BulletedItem,
    Divider,
)
from ultimate_notion.blocks import (
    Image as UnoImage,
)
from ultimate_notion.blocks import (
    Paragraph as UnoParagraph,
)
from ultimate_notion.rich_text import text

from sphinx_notion._upload import (
    _block_with_uploaded_file,
    _calculate_file_sha,
    _calculate_file_sha_from_url,
    _files_match,
    _find_matching_prefix_and_suffix_lengths,
    _get_uploaded_cover,
    _is_existing_equivalent,
)


def _clear_sha_caches() -> None:
    """Clear caches for SHA calculation functions."""
    _calculate_file_sha.cache_clear()
    _calculate_file_sha_from_url.cache_clear()


def test_calculate_file_sha(tmp_path: Path) -> None:
    """Test SHA256 calculation for files."""
    _clear_sha_caches()
    content = b"hello world"
    file_path = tmp_path / "test.txt"
    file_path.write_bytes(data=content)
    expected = hashlib.sha256(content).hexdigest()
    assert _calculate_file_sha(file_path=file_path) == expected


def test_calculate_file_sha_from_url() -> None:
    """Test SHA256 calculation from URL."""
    _clear_sha_caches()
    content = b"hello world"
    expected = hashlib.sha256(content).hexdigest()

    mock_response = MagicMock()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_content = MagicMock(
        return_value=[content, b"", content],
    )

    sha256 = hashlib.sha256()
    sha256.update(content)
    sha256.update(content)
    expected = sha256.hexdigest()

    with patch(
        target="sphinx_notion._upload.requests.get",
        return_value=mock_response,
    ):
        result = _calculate_file_sha_from_url(
            file_url="https://example.com/file.txt",
        )
    assert result == expected


def test_files_match_true(tmp_path: Path) -> None:
    """Test files_match when SHA hashes match."""
    _clear_sha_caches()
    content = b"matching content"
    file_path = tmp_path / "local.txt"
    file_path.write_bytes(data=content)
    expected_sha = hashlib.sha256(content).hexdigest()

    with patch(
        target="sphinx_notion._upload._calculate_file_sha_from_url",
        return_value=expected_sha,
    ):
        result = _files_match(
            existing_file_url="https://example.com/file.txt",
            local_file_path=file_path,
        )
    assert result is True


def test_files_match_false(tmp_path: Path) -> None:
    """Test files_match when SHA hashes differ."""
    _clear_sha_caches()
    file_path = tmp_path / "local.txt"
    file_path.write_bytes(data=b"local content")

    with patch(
        target="sphinx_notion._upload._calculate_file_sha_from_url",
        return_value="0000000000000000000000000000000000000000000000000000000000000000",
    ):
        result = _files_match(
            existing_file_url="https://example.com/file.txt",
            local_file_path=file_path,
        )
    assert result is False


def test_is_existing_equivalent_type_mismatch() -> None:
    """Test type mismatch returns False."""
    result = _is_existing_equivalent(
        existing_page_block=Divider(),
        local_block=UnoParagraph(text=text(text="x")),
    )
    assert result is False


def test_is_existing_equivalent_simple_block_equal() -> None:
    """Test equal simple blocks return True."""
    result = _is_existing_equivalent(
        existing_page_block=Divider(),
        local_block=Divider(),
    )
    assert result is True


def test_is_existing_equivalent_simple_block_not_equal() -> None:
    """Test unequal simple blocks return False."""
    result = _is_existing_equivalent(
        existing_page_block=Bookmark("https://a.com"),
        local_block=Bookmark("https://b.com"),
    )
    assert result is False


def test_is_existing_equivalent_file_block_matching(
    tmp_path: Path,
) -> None:
    """Test matching file blocks return True."""
    _clear_sha_caches()
    local_file = tmp_path / "img.png"
    local_file.write_bytes(data=b"image data")
    local_url = local_file.as_uri()

    local_block = UnoImage(file=ExternalFile(url=local_url))
    existing_block = UnoImage(
        file=NotionFile(url="https://notion.so/img.png"),
    )

    with patch(
        target="sphinx_notion._upload._files_match",
        return_value=True,
    ):
        result = _is_existing_equivalent(
            existing_page_block=existing_block,
            local_block=local_block,
        )
    assert result is True


def test_is_existing_equivalent_file_block_not_notion_file(
    tmp_path: Path,
) -> None:
    """Test non-Notion file blocks return False."""
    _clear_sha_caches()
    local_file = tmp_path / "img.png"
    local_file.write_bytes(data=b"image data")
    local_url = local_file.as_uri()

    local_block = UnoImage(file=ExternalFile(url=local_url))
    existing_block = UnoImage(
        file=ExternalFile(url="https://example.com/img.png"),
    )

    result = _is_existing_equivalent(
        existing_page_block=existing_block,
        local_block=local_block,
    )
    assert result is False


def test_is_existing_equivalent_file_block_name_mismatch(
    tmp_path: Path,
) -> None:
    """Test file blocks with name mismatch return False."""
    _clear_sha_caches()
    local_file = tmp_path / "img.png"
    local_file.write_bytes(data=b"image data")
    local_url = local_file.as_uri()

    local_block = UnoImage(file=ExternalFile(url=local_url, name="a.png"))
    existing_block = UnoImage(
        file=NotionFile(url="https://notion.so/img.png", name="b.png"),
    )

    result = _is_existing_equivalent(
        existing_page_block=existing_block,
        local_block=local_block,
    )
    assert result is False


def test_is_existing_equivalent_file_block_caption_mismatch(
    tmp_path: Path,
) -> None:
    """Test file blocks with caption mismatch return False."""
    _clear_sha_caches()
    local_file = tmp_path / "img.png"
    local_file.write_bytes(data=b"image data")
    local_url = local_file.as_uri()

    local_block = UnoImage(
        file=ExternalFile(url=local_url),
        caption="caption A",
    )
    existing_block = UnoImage(
        file=NotionFile(url="https://notion.so/img.png"),
        caption="caption B",
    )

    result = _is_existing_equivalent(
        existing_page_block=existing_block,
        local_block=local_block,
    )
    assert result is False


def test_is_existing_equivalent_file_block_external_url() -> None:
    """Test external file blocks return True if URLs match."""
    block_a = UnoImage(file=ExternalFile(url="https://example.com/img.png"))
    block_b = UnoImage(file=ExternalFile(url="https://example.com/img.png"))

    result = _is_existing_equivalent(
        existing_page_block=block_a,
        local_block=block_b,
    )
    assert result is True


def test_find_matching_suffix() -> None:
    """Test matching suffix detection."""
    matching_block_a = Divider()
    matching_block_b = Divider()

    existing = [
        UnoParagraph(text=text(text="old")),
        matching_block_a,
    ]
    local = [
        UnoParagraph(text=text(text="new")),
        matching_block_b,
    ]

    result = _find_matching_prefix_and_suffix_lengths(
        existing_blocks=existing,
        local_blocks=local,
    )
    assert result.prefix == 0
    assert result.suffix == 1


def test_is_existing_equivalent_parent_block_equal() -> None:
    """Test equal parent blocks return True."""
    existing = BulletedItem(text=text(text="item"))
    existing.append(blocks=[Divider()])

    local = BulletedItem(text=text(text="item"))
    local.append(blocks=[Divider()])

    result = _is_existing_equivalent(
        existing_page_block=existing,
        local_block=local,
    )
    assert result is True


def test_is_existing_equivalent_parent_block_different_children_count() -> (
    None
):
    """Test parent blocks with different children count."""
    existing = BulletedItem(text=text(text="item"))
    existing.append(blocks=[Divider()])

    local = BulletedItem(text=text(text="item"))
    local.append(blocks=[Divider(), Divider()])

    result = _is_existing_equivalent(
        existing_page_block=existing,
        local_block=local,
    )
    assert result is False


def test_get_uploaded_cover_unchanged(tmp_path: Path) -> None:
    """Test cover unchanged returns None."""
    _clear_sha_caches()
    cover_file = tmp_path / "cover.png"
    cover_file.write_bytes(data=b"image data")

    mock_page = MagicMock()
    mock_page.cover = NotionFile(url="https://notion.so/cover.png")

    with patch(
        target="sphinx_notion._upload._files_match",
        return_value=True,
    ):
        result = _get_uploaded_cover(
            page=mock_page,
            cover=cover_file,
            session=MagicMock(),
        )
    assert result is None


def test_block_with_uploaded_file_https_url() -> None:
    """Test HTTPS file blocks return unchanged."""
    block = UnoImage(file=ExternalFile(url="https://example.com/img.png"))
    result = _block_with_uploaded_file(
        block=block,
        session=MagicMock(spec=Session),
    )
    assert result is block
