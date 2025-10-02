"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import json
import sys
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
from ultimate_notion.file import UploadedFile
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock

if TYPE_CHECKING:
    from ultimate_notion.database import Database
    from ultimate_notion.page import Page


@beartype
def _upload_local_file(
    *,
    url: str,
    session: Session,
) -> UploadedFile | None:
    """
    Upload a local file and return the uploaded file object.
    """
    parsed = urlparse(url=url)
    if parsed.scheme != "file":
        return None

    # Ignore ``mypy`` error as the keyword arguments are different across
    # Python versions and platforms.
    file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]
    with file_path.open(mode="rb") as f:
        uploaded_file = session.upload(
            file=f,
            file_name=file_path.name,
        )

    uploaded_file.wait_until_uploaded()
    return uploaded_file


@beartype
def _convert_anchor_links_in_rich_text(
    *,
    rich_text: list[dict[str, Any]],
    anchor_to_block_id_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Convert anchor:// links in rich text to proper Notion block URLs.

    This function processes rich text content and replaces anchor://
    links with proper Notion internal links using the provided mapping.
    """
    converted_rich_text = []

    for text_segment in rich_text:
        if text_segment.get("type") == "text" and "href" in text_segment:
            href = text_segment["href"]
            if href.startswith("anchor://"):
                anchor_name = href[9:]  # Remove "anchor://" prefix
                if anchor_name in anchor_to_block_id_map:
                    # Convert to proper Notion internal link format
                    block_id = anchor_to_block_id_map[anchor_name]
                    text_segment["href"] = f"https://www.notion.so/{block_id}"

        converted_rich_text.append(text_segment)

    return converted_rich_text


@beartype
def _convert_anchor_links_in_block(
    *,
    block_details: dict[str, Any],
    anchor_to_block_id_map: dict[str, str],
) -> dict[str, Any]:
    """Convert anchor:// links in a block to proper Notion block URLs.

    This function recursively processes block content to convert
    anchor:// links to proper Notion internal links.
    """
    converted_block = block_details.copy()

    # Process rich text content in various block types
    for block_data in converted_block.values():
        if isinstance(block_data, dict):
            # Handle rich text content
            if "rich_text" in block_data and isinstance(
                block_data["rich_text"], list
            ):
                block_data["rich_text"] = _convert_anchor_links_in_rich_text(
                    rich_text=block_data["rich_text"],
                    anchor_to_block_id_map=anchor_to_block_id_map,
                )

            # Handle children blocks recursively
            if "children" in block_data and isinstance(
                block_data["children"], list
            ):
                block_data["children"] = [
                    _convert_anchor_links_in_block(
                        block_details=child,
                        anchor_to_block_id_map=anchor_to_block_id_map,
                    )
                    for child in block_data["children"]
                ]

    return converted_block


@beartype
def _build_anchor_to_block_id_mapping(
    *,
    blocks: list[dict[str, Any]],
) -> dict[str, str]:
    """Build a mapping from anchor names to Notion block IDs.

    This function scans all blocks to find anchor definitions and maps
    them to their corresponding Notion block IDs.
    """
    # This is a placeholder implementation
    # In a real implementation, you would need to:
    # 1. Scan all blocks for anchor definitions
    # 2. Extract anchor names and their corresponding block IDs
    # 3. Build the mapping dictionary

    # For now, we'll return an empty mapping
    # A full implementation would require:
    # - Parsing block content for anchor definitions
    # - Extracting block IDs from Notion blocks
    # - Building the mapping between anchor names and block IDs

    del blocks  # Unused for now
    return {}


@beartype
def _block_from_details(
    *,
    details: dict[str, Any],
    session: Session,
) -> Block:
    """Create a Block from a serialized block details.

    Upload any required local files.
    """
    block = Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))

    if isinstance(block, (UnoImage, UnoVideo, UnoAudio, UnoPDF)):
        uploaded_file = _upload_local_file(url=block.url, session=session)
        if uploaded_file is not None:
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

    # Convert anchor:// links to proper Notion block URLs
    anchor_mapping = _build_anchor_to_block_id_mapping(blocks=blocks)
    converted_blocks = [
        _convert_anchor_links_in_block(
            block_details=block,
            anchor_to_block_id_map=anchor_mapping,
        )
        for block in blocks
    ]

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
        sys.stdout.write(f"Created new page: '{title}' ({page.url})\n")

    if icon:
        page.icon = Emoji(emoji=icon)

    block_objs = [
        _block_from_details(details=details, session=session)
        for details in converted_blocks
    ]

    match_until_index = 0
    for index, existing_page_block in enumerate(iterable=page.children):
        if (
            index < len(converted_blocks)
            and existing_page_block == block_objs[index]
        ):
            match_until_index = index
        else:
            break

    sys.stdout.write(
        f"Matching blocks until index {match_until_index} for page '{title}'\n"
    )
    for existing_page_block in page.children[match_until_index + 1 :]:
        existing_page_block.delete()

    page.append(blocks=block_objs[match_until_index + 1 :])
    sys.stdout.write(f"Updated existing page: '{title}' ({page.url})\n")
