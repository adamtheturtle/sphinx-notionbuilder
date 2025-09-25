"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname

import click
from beartype import beartype
from ultimate_notion import Emoji, Session
from ultimate_notion.blocks import Block
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock


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

    if isinstance(block, UnoImage):
        parsed = urlparse(url=block.url)
        if parsed.scheme == "file":
            file_path = Path(url2pathname(pathname=parsed.path))
            with file_path.open(mode="rb") as f:
                uploaded_file = session.upload(
                    file=f,
                    file_name=file_path.name,
                )

            uploaded_file.wait_until_uploaded()
            return UnoImage(file=uploaded_file, caption=block.caption)
    elif isinstance(block, UnoVideo):
        parsed = urlparse(url=block.url)
        if parsed.scheme == "file":
            file_path = Path(url2pathname(pathname=parsed.path))
            with file_path.open(mode="rb") as f:
                uploaded_file = session.upload(
                    file=f,
                    file_name=file_path.name,
                )

            uploaded_file.wait_until_uploaded()
            return UnoVideo(file=uploaded_file, caption=block.caption)

    return block


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
    "--parent-page-id",
    help="Parent page ID (integration connected)",
    required=True,
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
    parent_page_id: str,
    title: str,
    icon: str | None = None,
) -> None:
    """
    Upload documentation to Notion.
    """
    session = Session()

    blocks = json.loads(s=file.read_text(encoding="utf-8"))

    parent_page = session.get_page(page_ref=parent_page_id)
    pages_matching_title = [
        child_page
        for child_page in parent_page.subpages
        if child_page.title == title
    ]

    if pages_matching_title:
        msg = (
            f"Expected 1 page matching title {title}, but got "
            f"{len(pages_matching_title)}"
        )
        assert len(pages_matching_title) == 1, msg
        (page,) = pages_matching_title
    else:
        page = session.create_page(parent=parent_page, title=title)
        sys.stdout.write(f"Created new page: {title} (ID: {page.id})\n")

    if icon:
        page.icon = Emoji(emoji=icon)

    for child in page.children:
        child.delete()

    block_objs = [
        _block_from_details(details=details, session=session)
        for details in blocks
    ]

    page.append(blocks=block_objs)
    sys.stdout.write(f"Updated existing page: {title} (ID: {page.id})\n")
