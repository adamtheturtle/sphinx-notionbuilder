"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import hashlib
import json
from enum import Enum
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from urllib.request import url2pathname
from uuid import UUID

import click
from beartype import beartype
from notion_client.errors import APIResponseError
from ultimate_notion import Emoji, Session
from ultimate_notion.blocks import PDF as UnoPDF  # noqa: N811
from ultimate_notion.blocks import Audio as UnoAudio
from ultimate_notion.blocks import Block
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock

if TYPE_CHECKING:
    from ultimate_notion.database import Database
    from ultimate_notion.page import Page

_FILE_BLOCK_TYPES = (UnoImage, UnoVideo, UnoAudio, UnoPDF)
_FileBlock = UnoImage | UnoVideo | UnoAudio | UnoPDF


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
def _clean_deleted_blocks_from_mapping(
    *,
    sha_to_block_id: dict[str, str],
    session: Session,
) -> dict[str, str]:
    """Remove deleted blocks from SHA mapping.

    Returns a new dictionary with only existing blocks.
    """
    cleaned_mapping = sha_to_block_id.copy()
    deleted_block_shas: set[str] = set()

    for sha, block_id_str in sha_to_block_id.items():
        block_id = UUID(hex=block_id_str)
        try:
            session.api.blocks.retrieve(block=block_id)
        except APIResponseError:
            deleted_block_shas.add(sha)
            msg = f"Block {block_id} does not exist, removing from SHA mapping"
            click.echo(message=msg)

    for deleted_block_sha in deleted_block_shas:
        del cleaned_mapping[deleted_block_sha]

    return cleaned_mapping


@beartype
def _find_last_matching_block_index(
    *,
    existing_blocks: list[Block] | tuple[Block, ...],
    local_blocks: list[Block],
    sha_to_block_id: dict[str, str],
) -> int | None:
    """Find the last index where existing blocks match local blocks.

    Returns the last index where blocks are equivalent, or None if no
    blocks match.
    """
    last_matching_index: int | None = None
    for index, existing_page_block in enumerate(iterable=existing_blocks):
        if index < len(local_blocks) and (
            _is_existing_equivalent(
                existing_page_block=existing_page_block,
                local_block=local_blocks[index],
                sha_to_block_id=sha_to_block_id,
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
    sha_to_block_id: dict[str, str],
) -> bool:
    """
    Check if a local block is equivalent to an existing page block.
    """
    if existing_page_block == local_block:
        return True

    if isinstance(
        local_block, _FILE_BLOCK_TYPES
    ) and local_block.url.startswith("file://"):
        parsed = urlparse(url=local_block.url)
        file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]
        file_sha = _calculate_file_sha(file_path=file_path)
        existing_page_block_id_with_file_sha = sha_to_block_id.get(file_sha)
        if not existing_page_block_id_with_file_sha:
            return False
        if (
            UUID(hex=existing_page_block_id_with_file_sha)
            == existing_page_block.id
        ):
            return True

    return False


@beartype
def _block_from_details(
    *,
    details: dict[str, Any],
    session: Session,
) -> Block:
    """Create a Block from a serialized block details.

    Get any required local files from SHA mapping or upload them.
    """
    block = Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))

    if isinstance(block, _FILE_BLOCK_TYPES) and block.url.startswith(
        "file://"
    ):
        parsed = urlparse(url=block.url)
        # Ignore ``mypy`` error as the keyword arguments are different across
        # Python versions and platforms.
        file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]

        with file_path.open(mode="rb") as file_stream:
            uploaded_file = session.upload(
                file=file_stream,
                file_name=file_path.name,
            )

        uploaded_file.wait_until_uploaded()

        return block.__class__(file=uploaded_file, caption=block.caption)

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
@click.option(
    "--sha-mapping",
    help="JSON file mapping file SHAs to Notion block IDs (required)",
    required=True,
    type=click.Path(
        exists=True,
        path_type=Path,
        file_okay=True,
        dir_okay=False,
    ),
)
@beartype
def main(
    *,
    file: Path,
    parent_id: str,
    parent_type: _ParentType,
    title: str,
    icon: str | None = None,
    sha_mapping: Path,
) -> None:
    """
    Upload documentation to Notion.
    """
    session = Session()

    sha_mapping_content = sha_mapping.read_text(encoding="utf-8")
    if sha_mapping_content.strip():
        sha_to_block_id: dict[str, str] = dict(
            json.loads(s=sha_mapping_content)
        )
    else:
        sha_to_block_id = {}

    sha_to_block_id = _clean_deleted_blocks_from_mapping(
        sha_to_block_id=sha_to_block_id,
        session=session,
    )

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
        sha_to_block_id=sha_to_block_id,
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
        _block_from_details(details=details, session=session)
        for details in blocks[delete_start_index:]
    ]
    page.append(blocks=block_objs_to_upload)

    for uploaded_block_index, uploaded_block in enumerate(
        iterable=block_objs_to_upload
    ):
        if isinstance(uploaded_block, _FILE_BLOCK_TYPES):
            pre_uploaded_block = block_objs[
                delete_start_index + uploaded_block_index
            ]
            assert isinstance(pre_uploaded_block, _FILE_BLOCK_TYPES)
            if pre_uploaded_block.url.startswith("file://"):
                parsed = urlparse(url=pre_uploaded_block.url)
                file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]
                file_sha = _calculate_file_sha(file_path=file_path)
                sha_to_block_id[file_sha] = str(object=uploaded_block.id)
                click.echo(
                    message=(
                        f"Updated SHA mapping for {file_path.name}:"
                        f"{uploaded_block.id}"
                    )
                )

    sha_mapping.write_text(
        data=json.dumps(obj=sha_to_block_id, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    click.echo(message=f"Updated existing page: '{title}' ({page.url})")
