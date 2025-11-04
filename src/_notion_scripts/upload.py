"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import hashlib
import json
import mimetypes
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from urllib.request import url2pathname

import click
import cloup
import requests
from beartype import beartype
from ultimate_notion import Emoji, ExternalFile, NotionFile, Session
from ultimate_notion.blocks import PDF as UnoPDF  # noqa: N811
from ultimate_notion.blocks import Audio as UnoAudio
from ultimate_notion.blocks import Block, ParentBlock
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.file import UploadedFile
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock
from ultimate_notion.page import Page

if TYPE_CHECKING:
    from ultimate_notion.database import Database

_FILE_BLOCK_TYPES = (UnoImage, UnoVideo, UnoAudio, UnoPDF)


@beartype
def _block_without_children(
    *,
    block: ParentBlock,
) -> ParentBlock:
    """
    Return a copy of a block without children.
    """
    serialized_block = block.obj_ref.serialize_for_api()
    if block.children:
        serialized_block[serialized_block["type"]]["children"] = []

    # Delete the ID, else the block will have the children from Notion.
    if "id" in serialized_block:
        del serialized_block["id"]

    block_without_children = Block.wrap_obj_ref(
        UnoObjAPIBlock.model_validate(obj=serialized_block)
    )
    assert isinstance(block_without_children, ParentBlock)
    assert not block_without_children.children
    return block_without_children


@beartype
@cache
def _calculate_file_sha(*, file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.
    """
    sha256_hash = hashlib.sha256()
    with file_path.open(mode="rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


@beartype
@cache
def _calculate_file_sha_from_url(*, file_url: str) -> str:
    """
    Calculate SHA-256 hash of a file from a URL.
    """
    sha256_hash = hashlib.sha256()
    with requests.get(url=file_url, stream=True, timeout=10) as response:
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


@beartype
def _files_match(*, existing_file_url: str, local_file_path: Path) -> bool:
    """
    Check if an existing file matches a local file by comparing SHA-256 hashes.
    """
    existing_file_sha = _calculate_file_sha_from_url(
        file_url=existing_file_url
    )
    local_file_sha = _calculate_file_sha(file_path=local_file_path)
    return existing_file_sha == local_file_sha


@beartype
def _find_last_matching_block_index(
    *,
    existing_blocks: list[Block] | tuple[Block, ...],
    local_blocks: list[Block],
) -> int | None:
    """Find the last index where existing blocks match local blocks.

    Returns the last index where blocks are equivalent, or None if no
    blocks match.
    """
    last_matching_index: int | None = None
    for index, existing_page_block in enumerate(iterable=existing_blocks):
        click.echo(
            message=(
                f"Checking block {index + 1} of {len(existing_blocks)} for "
                "equivalence"
            ),
        )
        if index < len(local_blocks) and (
            _is_existing_equivalent(
                existing_page_block=existing_page_block,
                local_block=local_blocks[index],
            )
        ):
            last_matching_index = index
        else:
            break
    return last_matching_index


@beartype
def _is_existing_equivalent(
    *,
    existing_page_block: Block,
    local_block: Block,
) -> bool:
    """
    Check if a local block is equivalent to an existing page block.
    """
    if type(existing_page_block) is not type(local_block):
        return False

    if isinstance(local_block, _FILE_BLOCK_TYPES):
        parsed = urlparse(url=local_block.url)
        if parsed.scheme == "file":
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
            return _files_match(
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
        ) or (len(existing_page_block.children) != len(local_block.children)):
            return False

        return all(
            _is_existing_equivalent(
                existing_page_block=existing_child_block,
                local_block=local_child_block,
            )
            for (existing_child_block, local_child_block) in zip(
                existing_page_block.children,
                local_block.children,
                strict=False,
            )
        )

    return existing_page_block == local_block


@beartype
def _get_mime_type_for_upload(*, file_name: str) -> str | None:
    """Get MIME type for file upload.

    Ultimate Notion does not support SVG files, so we need to provide
    the MIME type ourselves for SVG files. See
    https://github.com/ultimate-notion/ultimate-notion/issues/141.
    """
    mime_type, _ = mimetypes.guess_type(url=file_name)
    if mime_type != "image/svg+xml":
        mime_type = None
    return mime_type


def _get_uploaded_cover(
    *,
    page: Page,
    cover: Path,
    session: Session,
) -> UploadedFile | None:
    """
    Get uploaded cover file, or None if it matches the existing cover.
    """
    if (
        page.cover is not None
        and isinstance(page.cover, NotionFile)
        and _files_match(
            existing_file_url=page.cover.url, local_file_path=cover
        )
    ):
        return None

    mime_type = _get_mime_type_for_upload(file_name=cover.name)

    with cover.open(mode="rb") as file_stream:
        uploaded_cover = session.upload(
            file=file_stream,
            file_name=cover.name,
            mime_type=mime_type,
        )

    uploaded_cover.wait_until_uploaded()
    return uploaded_cover


@beartype
def _check_all_blocks_recursive(
    *,
    blocks: Sequence[Block | Page],
) -> None:
    """
    Recursively check that all items are Blocks, including nested children.
    """
    for child in blocks:
        if not isinstance(child, Block):
            non_block_page_child_error = (
                f"We only support pages which only contain Blocks. "
                f"Found {type(child)}. "
            )
            raise click.ClickException(message=non_block_page_child_error)

        if isinstance(child, ParentBlock) and child.children:
            _check_all_blocks_recursive(blocks=child.children)


@beartype
def _block_with_uploaded_file(
    *,
    block: Block,
    session: Session,
) -> Block:
    """
    Replace a file block with an uploaded file block.
    """
    if isinstance(block, _FILE_BLOCK_TYPES):
        parsed = urlparse(url=block.url)
        if parsed.scheme == "file":
            # Ignore ``mypy`` error as the keyword arguments are different
            # across Python versions and platforms.
            file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]

            mime_type = _get_mime_type_for_upload(file_name=file_path.name)

            with file_path.open(mode="rb") as file_stream:
                uploaded_file = session.upload(
                    file=file_stream,
                    file_name=file_path.name,
                    mime_type=mime_type,
                )

            uploaded_file.wait_until_uploaded()

            block = block.__class__(file=uploaded_file, caption=block.caption)

    elif isinstance(block, ParentBlock) and block.children:
        new_child_blocks = [
            _block_with_uploaded_file(block=child_block, session=session)
            for child_block in block.children
        ]
        block = _block_without_children(block=block)
        block.append(blocks=new_child_blocks)

    return block


@cloup.command()
@cloup.option(
    "--file",
    help="JSON File to upload",
    required=True,
    type=cloup.Path(
        exists=True,
        path_type=Path,
        file_okay=True,
        dir_okay=False,
    ),
)
@cloup.option_group(
    "Parent location",
    cloup.option(
        "--parent-page-id",
        help="Parent page ID (integration connected)",
    ),
    cloup.option(
        "--parent-database-id",
        help="Parent database ID (integration connected)",
    ),
    constraint=cloup.constraints.RequireExactly(n=1),
)
@cloup.option(
    "--title",
    help="Title of the page to update (or create if it does not exist)",
    required=True,
)
@cloup.option(
    "--icon",
    help="Icon of the page",
    required=False,
)
@cloup.option_group(
    "Cover image",
    cloup.option(
        "--cover-path",
        help="Cover image file path for the page",
        required=False,
        type=cloup.Path(
            exists=True,
            path_type=Path,
            file_okay=True,
            dir_okay=False,
        ),
    ),
    cloup.option(
        "--cover-url",
        help="Cover image URL for the page",
        required=False,
    ),
    constraint=cloup.constraints.mutually_exclusive,
)
@cloup.option(
    "--cancel-on-discussion",
    help=(
        "Cancel upload with error if blocks to be deleted have discussion "
        "threads"
    ),
    is_flag=True,
    default=False,
)
@beartype
def main(
    *,
    file: Path,
    parent_page_id: str | None,
    parent_database_id: str | None,
    title: str,
    icon: str | None,
    cover_path: Path | None,
    cover_url: str | None,
    cancel_on_discussion: bool,
) -> None:
    """
    Upload documentation to Notion.
    """
    session = Session()

    blocks = json.loads(s=file.read_text(encoding="utf-8"))

    parent: Page | Database
    if parent_page_id:
        parent = session.get_page(page_ref=parent_page_id)
        subpages = parent.subpages
    else:
        assert parent_database_id is not None
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
    else:
        page = session.create_page(parent=parent, title=title)
        click.echo(message=f"Created new page: '{title}' ({page.url})")

    page.icon = Emoji(emoji=icon) if icon else None
    if cover_path:
        page.cover = _get_uploaded_cover(
            page=page, cover=cover_path, session=session
        )
    elif cover_url:
        page.cover = ExternalFile(url=cover_url)
    else:
        page.cover = None

    block_objs = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))
        for details in blocks
    ]

    _check_all_blocks_recursive(blocks=page.children)

    last_matching_index = _find_last_matching_block_index(
        existing_blocks=page.children,
        local_blocks=block_objs,
    )

    click.echo(
        message=(
            f"Matching blocks until index {last_matching_index} for page "
            f"'{title}'"
        ),
    )
    delete_start_index = (last_matching_index or -1) + 1
    blocks_to_delete = page.children[delete_start_index:]
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
        raise click.ClickException(message=error_message)

    for existing_page_block in blocks_to_delete:
        existing_page_block.delete()

    block_objs_to_upload = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))
        for details in blocks[delete_start_index:]
    ]
    block_objs_with_uploaded_files = [
        _block_with_uploaded_file(block=block, session=session)
        for block in block_objs_to_upload
    ]
    page.append(blocks=block_objs_with_uploaded_files)

    click.echo(message=f"Updated existing page: '{title}' ({page.url})")
