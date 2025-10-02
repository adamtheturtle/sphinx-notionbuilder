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
        for details in blocks
    ]

    match_until_index = 0
    for index, existing_page_block in enumerate(iterable=page.children):
        if index < len(blocks) and existing_page_block == block_objs[index]:
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
