"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from urllib.request import url2pathname

import requests
from beartype import beartype
from ultimate_notion import Emoji, ExternalFile, NotionFile, Session
from ultimate_notion.blocks import PDF as UnoPDF  # noqa: N811
from ultimate_notion.blocks import Audio as UnoAudio
from ultimate_notion.blocks import Block, ParentBlock
from ultimate_notion.blocks import File as UnoFile
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.file import UploadedFile
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock
from ultimate_notion.page import Page

if TYPE_CHECKING:
    from ultimate_notion.database import Database

_LOGGER = logging.getLogger(name=__name__)

_FILE_BLOCK_TYPES = (UnoImage, UnoVideo, UnoAudio, UnoPDF, UnoFile)


@dataclass(frozen=True, slots=True)
class _MatchLengths:
    """Matching prefix/suffix lengths for block diffing."""

    prefix: int
    suffix: int


class PageHasSubpagesError(Exception):
    """Raised when a page has subpages, which is not supported."""


class PageHasDatabasesError(Exception):
    """Raised when a page has databases, which is not supported."""


class DiscussionsExistError(Exception):
    """Raised when blocks to delete have discussions and
    cancel_on_discussion
    is True.
    """


@beartype
def _block_without_children(
    *,
    block: ParentBlock,
) -> ParentBlock:
    """Return a copy of a block without children."""
    serialized_block = block.obj_ref.serialize_for_api()
    if block.has_children:
        serialized_block[serialized_block["type"]]["children"] = []

    # Delete the ID, else the block will have the children from Notion.
    if "id" in serialized_block:
        del serialized_block["id"]

    block_without_children = Block.wrap_obj_ref(
        # See https://github.com/ultimate-notion/ultimate-notion/issues/177
        UnoObjAPIBlock.model_validate(obj=serialized_block)  # ty: ignore[invalid-argument-type]
    )
    assert isinstance(block_without_children, ParentBlock)
    assert not block_without_children.blocks
    return block_without_children


@beartype
@cache
def _calculate_file_sha(
    *,
    file_path: Path,
) -> str:  # pragma: no cover - live file duplicate check
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with file_path.open(mode="rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


@beartype
@cache
def _calculate_file_sha_from_url(
    *,
    file_url: str,
) -> str:  # pragma: no cover - requires network file download
    """Calculate SHA-256 hash of a file from a URL."""
    sha256_hash = hashlib.sha256()
    with requests.get(url=file_url, stream=True, timeout=10) as response:
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


@beartype
def _files_match(
    *,
    existing_file_url: str,
    local_file_path: Path,
) -> bool:  # pragma: no cover - live file hash comparison path
    """
    Check if an existing file matches a local file by comparing SHA-256
    hashes.
    """
    existing_file_sha = (
        _calculate_file_sha_from_url(  # pragma: no cover - network path
            file_url=existing_file_url
        )
    )
    local_file_sha = _calculate_file_sha(file_path=local_file_path)
    return existing_file_sha == local_file_sha


@beartype
def _find_matching_prefix_and_suffix_lengths(
    *,
    existing_blocks: Sequence[Block],
    local_blocks: Sequence[Block],
) -> _MatchLengths:
    """Find the lengths of matching prefix and suffix between block lists.

    Returns matching lengths where:
    - `prefix`: number of matching blocks from the start
    - `suffix`: number of matching blocks from the end (not overlapping
      with prefix)
    """
    min_len = min(len(existing_blocks), len(local_blocks))

    prefix_len = 0
    for i in range(min_len):
        if _is_existing_equivalent(
            existing_page_block=existing_blocks[i],
            local_block=local_blocks[i],
        ):
            prefix_len += 1
        else:
            break

    suffix_len = 0
    for i in range(1, min_len - prefix_len + 1):
        if _is_existing_equivalent(
            existing_page_block=existing_blocks[-i],
            local_block=local_blocks[-i],
        ):
            suffix_len += 1
        else:
            break

    return _MatchLengths(prefix=prefix_len, suffix=suffix_len)


@beartype
def _is_existing_equivalent(
    *,
    existing_page_block: Block,
    local_block: Block,
) -> bool:
    """Check if a local block is equivalent to an existing page block."""
    if type(existing_page_block) is not type(local_block):
        return False

    if isinstance(local_block, _FILE_BLOCK_TYPES):
        parsed = urlparse(url=local_block.url)
        if parsed.scheme == "file":  # pragma: no cover - local duplicate check
            assert isinstance(existing_page_block, _FILE_BLOCK_TYPES)

            if (
                not isinstance(existing_page_block.file_info, NotionFile)
                or (
                    existing_page_block.file_info.name
                    != local_block.file_info.name
                )
                or (
                    existing_page_block.file_info.caption
                    != local_block.file_info.caption
                )
            ):
                return False

            local_file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]
            return _files_match(  # pragma: no cover - network path
                existing_file_url=existing_page_block.file_info.url,
                local_file_path=local_file_path,
            )
    elif isinstance(existing_page_block, ParentBlock):
        assert isinstance(local_block, ParentBlock)
        existing_page_block_without_children = _block_without_children(
            block=existing_page_block,
        )

        local_block_without_children = _block_without_children(
            block=local_block,
        )

        if (
            existing_page_block_without_children
            != local_block_without_children
        ) or (len(existing_page_block.blocks) != len(local_block.blocks)):
            return False

        return all(
            _is_existing_equivalent(
                existing_page_block=existing_child_block,
                local_block=local_child_block,
            )
            for (existing_child_block, local_child_block) in zip(
                existing_page_block.blocks,
                local_block.blocks,
                strict=False,
            )
        )

    return existing_page_block == local_block


def _get_uploaded_cover(
    *,
    page: Page,
    cover: Path,
    session: Session,
) -> UploadedFile | None:
    """
    Get uploaded cover file, or None if it matches the existing
    cover.
    """
    if (  # pragma: no cover - remote cover check
        page.cover is not None
        and isinstance(page.cover, NotionFile)
        and _files_match(
            existing_file_url=page.cover.url, local_file_path=cover
        )
    ):
        _LOGGER.info("Cover image unchanged, skipping upload")
        return None

    _LOGGER.info("Uploading cover image '%s'", cover.name)
    with cover.open(mode="rb") as file_stream:
        uploaded_cover = session.upload(
            file=file_stream,
            file_name=cover.name,
        )

    uploaded_cover.wait_until_uploaded()
    _LOGGER.info("Cover image uploaded")
    return uploaded_cover


@beartype
def _block_with_uploaded_file(*, block: Block, session: Session) -> Block:
    """Replace a file block with an uploaded file block."""
    if isinstance(block, _FILE_BLOCK_TYPES):
        parsed = urlparse(url=block.url)
        if parsed.scheme == "file":
            # Ignore ``mypy`` error as the keyword arguments are different
            # across Python versions and platforms.
            file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]
            _LOGGER.info("Uploading file '%s'", file_path.name)

            with file_path.open(mode="rb") as file_stream:
                uploaded_file = session.upload(
                    file=file_stream,
                    file_name=file_path.name,
                )

            uploaded_file.wait_until_uploaded()
            _LOGGER.info("File '%s' uploaded", file_path.name)

            block = block.__class__(file=uploaded_file, caption=block.caption)

    elif isinstance(block, ParentBlock) and block.has_children:
        new_child_blocks = [
            _block_with_uploaded_file(block=child_block, session=session)
            for child_block in block.blocks
        ]
        block = _block_without_children(block=block)
        block.append(blocks=new_child_blocks)

    return block


@beartype
# pylint: disable-next=too-complex,too-many-branches,too-many-statements
def upload_to_notion(  # noqa: C901, PLR0912, PLR0915
    *,
    session: Session,
    blocks: Sequence[Block],
    parent_page_id: str | None,
    parent_database_id: str | None,
    title: str,
    icon: str | None,
    cover_path: Path | None,
    cover_url: str | None,
    cancel_on_discussion: bool,
) -> Page:
    """Upload documentation to Notion.

    Returns the page that was created or updated.

    Raises:
        PageHasSubpagesError: If the page has subpages.
        PageHasDatabasesError: If the page has databases.
        DiscussionsExistError: If blocks to delete have discussions and
            cancel_on_discussion is True.
    """
    parent: Page | Database
    if parent_page_id:
        _LOGGER.info("Fetching parent page '%s'", parent_page_id)
        parent = session.get_page(page_ref=parent_page_id)
        subpages = parent.subpages
    else:
        assert parent_database_id is not None
        _LOGGER.info("Fetching parent database '%s'", parent_database_id)
        parent = session.get_db(db_ref=parent_database_id)
        subpages = parent.get_all_pages().to_pages()

    pages_matching_title = [
        child_page for child_page in subpages if child_page.title == title
    ]

    if pages_matching_title:
        msg = (
            f"Expected 1 page matching title {title}, but got "
            f"{len(pages_matching_title)}"
        )
        assert len(pages_matching_title) == 1, msg
        (page,) = pages_matching_title
        _LOGGER.info("Found existing page '%s'", title)
    else:
        _LOGGER.info("Creating new page '%s'", title)
        page = session.create_page(parent=parent, title=title)

    if icon:
        _LOGGER.info("Setting page icon to '%s'", icon)
    page.icon = Emoji(emoji=icon) if icon else None
    if cover_path:
        page.cover = _get_uploaded_cover(
            page=page, cover=cover_path, session=session
        )
    elif cover_url:
        _LOGGER.info("Setting page cover to '%s'", cover_url)
        page.cover = ExternalFile(url=cover_url)
    else:
        page.cover = None

    if page.subpages:
        raise PageHasSubpagesError

    if page.subdbs:
        raise PageHasDatabasesError

    _LOGGER.info("Syncing page blocks")
    existing_blocks = page.blocks
    _LOGGER.info(
        "Comparing %d existing blocks with %d local blocks",
        len(existing_blocks),
        len(blocks),
    )
    match_lengths = _find_matching_prefix_and_suffix_lengths(
        existing_blocks=existing_blocks,
        local_blocks=blocks,
    )
    prefix_len = match_lengths.prefix
    suffix_len = match_lengths.suffix

    # Can't use suffix matching without a prefix because the Notion API
    # has no way to insert before the first block.
    if prefix_len == 0:
        suffix_len = 0

    existing_end = len(existing_blocks) - suffix_len
    local_end = len(blocks) - suffix_len

    blocks_to_delete = existing_blocks[prefix_len:existing_end]
    blocks_to_upload = blocks[prefix_len:local_end]
    _LOGGER.info(
        "%d prefix and %d suffix blocks match, %d to delete, %d to upload",
        prefix_len,
        suffix_len,
        len(blocks_to_delete),
        len(blocks_to_upload),
    )
    blocks_to_delete_with_discussions = [
        block for block in blocks_to_delete if len(block.discussions) > 0
    ]

    if cancel_on_discussion and blocks_to_delete_with_discussions:
        total_discussions = sum(
            len(block.discussions)
            for block in blocks_to_delete_with_discussions
        )
        error_message = (
            f"Page '{title}' has {len(blocks_to_delete_with_discussions)} "
            f"block(s) to delete with {total_discussions} discussion "
            "thread(s). "
            f"Upload cancelled."
        )
        raise DiscussionsExistError(error_message)

    for block_index, existing_page_block in enumerate(
        iterable=blocks_to_delete
    ):
        _LOGGER.info(
            "Deleting block %d/%d",
            block_index + 1,
            len(blocks_to_delete),
        )
        existing_page_block.delete()

    _LOGGER.info("Preparing %d blocks for upload", len(blocks_to_upload))
    block_objs_with_uploaded_files = [
        _block_with_uploaded_file(block=block, session=session)
        for block in blocks_to_upload
    ]

    if block_objs_with_uploaded_files:
        _LOGGER.info(
            "Appending %d blocks to page",
            len(block_objs_with_uploaded_files),
        )
        after_block = (
            existing_blocks[prefix_len - 1] if prefix_len > 0 else None
        )
        page.append(
            blocks=block_objs_with_uploaded_files,
            after=after_block,
        )
    return page
