"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import hashlib
import json
import mimetypes
from enum import Enum
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from urllib.request import url2pathname

import click
import requests
from beartype import beartype
from ultimate_notion import Emoji, NotionFile, Session
from ultimate_notion.blocks import PDF as UnoPDF  # noqa: N811
from ultimate_notion.blocks import Audio as UnoAudio
from ultimate_notion.blocks import Block, ParentBlock
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock

if TYPE_CHECKING:
    from ultimate_notion.database import Database
    from ultimate_notion.page import Page

_FILE_BLOCK_TYPES = (UnoImage, UnoVideo, UnoAudio, UnoPDF)
_FileBlock = UnoImage | UnoVideo | UnoAudio | UnoPDF


@beartype
def _block_without_children(
    *,
    block: ParentBlock,
) -> ParentBlock:
    """
    Return a copy of a block without children.
    """
    serialized_block_without_children = block.obj_ref.serialize_for_api()

    # Delete the ID, else the block will have the children from Notion.
    if "id" in serialized_block_without_children:
        del serialized_block_without_children["id"]

    block_without_children = Block.wrap_obj_ref(
        UnoObjAPIBlock.model_validate(obj=serialized_block_without_children)
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
            local_file_sha = _calculate_file_sha(file_path=local_file_path)
            existing_file_sha = _calculate_file_sha_from_url(
                file_url=existing_page_block.file_info.url,
            )
            return local_file_sha == existing_file_sha
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

            # Ultimate Notion does not support SVG files, so we need to
            # provide the MIME type ourselves for SVG files.
            # See https://github.com/ultimate-notion/ultimate-notion/issues/141.
            mime_type, _ = mimetypes.guess_type(url=file_path.name)
            if mime_type != "image/svg+xml":
                mime_type = None

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


@beartype
class _ParentType(Enum):
    """
    Type of parent that new page will live under.
    """

    PAGE = "page"
    DATABASE = "database"


@click.command()
@click.option(
    "--file",
    help="JSON File to upload",
    required=True,
    type=click.Path(
        exists=True,
        path_type=Path,
        file_okay=True,
        dir_okay=False,
    ),
)
@click.option(
    "--parent-id",
    help="Parent page or database ID (integration connected)",
    required=True,
)
@click.option(
    "--parent-type",
    help="Parent type",
    required=True,
    type=click.Choice(choices=_ParentType, case_sensitive=False),
)
@click.option(
    "--title",
    help="Title of the page to update (or create if it does not exist)",
    required=True,
)
@click.option(
    "--icon",
    help="Icon of the page",
    required=False,
)
@beartype
def main(
    *,
    file: Path,
    parent_id: str,
    parent_type: _ParentType,
    title: str,
    icon: str | None = None,
) -> None:
    """
    Upload documentation to Notion.
    """
    session = Session()

    blocks = json.loads(s=file.read_text(encoding="utf-8"))

    parent: Page | Database
    match parent_type:
        case _ParentType.PAGE:
            parent = session.get_page(page_ref=parent_id)
            subpages = parent.subpages
        case _ParentType.DATABASE:
            parent = session.get_db(db_ref=parent_id)
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

    if icon:
        page.icon = Emoji(emoji=icon)

    block_objs = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))
        for details in blocks
    ]

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
    for existing_page_block in page.children[delete_start_index:]:
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
