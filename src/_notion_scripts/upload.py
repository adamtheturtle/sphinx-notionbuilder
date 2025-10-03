"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from urllib.request import url2pathname

import click
from beartype import beartype
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
def _file_block_exists(*, block_id: str, session: Session) -> bool:
    """
    Validate that a block ID still exists and is a file block.
    """
    block = session.api.blocks.retrieve(block=block_id)
    return isinstance(block, _FILE_BLOCK_TYPES)


@beartype
def _upload_file_and_get_block(
    *,
    block: _FileBlock,
    session: Session,
) -> Block:
    """
    Upload a file and return the corresponding block.
    """
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


@beartype
def _get_or_upload_file_block(
    *,
    block: _FileBlock,
    session: Session,
    sha_mapping: dict[str, str],
) -> Block:
    """
    Get an existing file block from SHA mapping or upload and create new.
    """
    parsed = urlparse(url=block.url)

    # Ignore ``mypy`` error as the keyword arguments are different across
    # Python versions and platforms.
    file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]
    file_sha = _calculate_file_sha(file_path=file_path)

    if file_sha in sha_mapping:
        block_id = sha_mapping[file_sha]
        if _file_block_exists(block_id=block_id, session=session):
            block_obj = session.api.blocks.retrieve(block=block_id)
            return Block.wrap_obj_ref(block_obj)

    return _upload_file_and_get_block(block=block, session=session)


@beartype
def _block_from_details(
    *,
    details: dict[str, Any],
    session: Session,
    sha_mapping: dict[str, str],
) -> Block:
    """Create a Block from a serialized block details.

    Get any required local files from SHA mapping or upload them.
    """
    block = Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))

    if isinstance(block, _FILE_BLOCK_TYPES) and block.url.startswith(
        "file://"
    ):
        return _get_or_upload_file_block(
            block=block,
            session=session,
            sha_mapping=sha_mapping,
        )

    return block


@beartype
def _equal_blocks(*, existing_page_block: Block, local_block: Block) -> bool:
    """
    Check if two blocks are equal.
    """
    return existing_page_block == local_block


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

    # Load SHA mapping (format: {sha: block_id})
    sha_mapping_content = sha_mapping.read_text(encoding="utf-8")
    if sha_mapping_content.strip():
        sha_mapping_dict: dict[str, str] = dict(
            json.loads(s=sha_mapping_content)
        )
    else:
        sha_mapping_dict = {}

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
        _block_from_details(
            details=details,
            session=session,
            sha_mapping=sha_mapping_dict,
        )
        for details in blocks
    ]

    last_matching_index: int | None = None
    for index, existing_page_block in enumerate(iterable=page.children):
        if index < len(blocks) and _equal_blocks(
            existing_page_block=existing_page_block,
            local_block=block_objs[index],
        ):
            last_matching_index = index
        else:
            break

    click.echo(
        message=(
            f"Matching blocks until index {last_matching_index} for page "
            f"'{title}'"
        ),
    )
    delete_start_index = (last_matching_index or -1) + 1
    for existing_page_block in page.children[delete_start_index:]:
        existing_page_block.delete()

    # Append new blocks and get updated block objects with IDs
    new_blocks = block_objs[delete_start_index:]
    if new_blocks:
        page.append(blocks=new_blocks)

        # Update SHA mapping with new block IDs
        for block in new_blocks:
            if (
                isinstance(block, _FILE_BLOCK_TYPES)
                and hasattr(block, "url")
                and block.url.startswith("file://")
            ):
                parsed = urlparse(url=block.url)
                file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]
                file_sha = _calculate_file_sha(file_path=file_path)
                # The block should now have an ID after being appended
                if hasattr(block, "id") and block.id:
                    block_id_str = str(object=block.id)
                    sha_mapping_dict[file_sha] = block_id_str
                    msg = (
                        f"Updated SHA mapping for {file_path.name}: "
                        f"{block_id_str}"
                    )
                    click.echo(message=msg)

        # Write updated SHA mapping back to file
        sha_mapping.write_text(
            data=json.dumps(obj=sha_mapping_dict, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    click.echo(message=f"Updated existing page: '{title}' ({page.url})")
