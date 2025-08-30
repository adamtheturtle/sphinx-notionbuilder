"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import json
import sys
from pathlib import Path
from typing import Any, TypedDict

import click
from beartype import beartype
from ultimate_notion import Session
from ultimate_notion.blocks import Block, ChildrenMixin
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock
from ultimate_notion.page import Page


class _SerializedBlockTreeNode(TypedDict):
    """
    A node in the block tree representing a Notion block with its children.
    """

    block: dict[str, Any]
    children: list["_SerializedBlockTreeNode"]


@beartype
def _batch_list[T](*, elements: list[T], batch_size: int) -> list[list[T]]:
    """
    Split a list into batches of a given size.
    """
    return [
        elements[start_index : start_index + batch_size]
        for start_index in range(0, len(elements), batch_size)
    ]


@beartype
def upload_blocks_recursively(
    parent: Page | ChildrenMixin[Any],
    block_details_list: list[_SerializedBlockTreeNode],
    session: Session,
    batch_size: int,
) -> None:
    """
    Upload blocks recursively, handling the new structure with block and
    children.
    """
    first_level_blocks: list[Block[Any]] = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details["block"]))  # pyright: ignore[reportUnknownMemberType]
        for details in block_details_list
    ]
    for block_batch in _batch_list(
        elements=first_level_blocks,
        batch_size=batch_size,
    ):
        parent.append(blocks=block_batch)  # pyright: ignore[reportUnknownMemberType]

    for uploaded_block_index, uploaded_block in enumerate(  # pyright: ignore[reportUnknownVariableType]
        iterable=parent.children  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
    ):
        block_details = block_details_list[uploaded_block_index]
        if block_details["children"]:
            block_obj = session.get_block(block_ref=uploaded_block.id)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            assert isinstance(block_obj, ChildrenMixin)
            upload_blocks_recursively(
                parent=block_obj,
                block_details_list=block_details["children"],
                session=session,
                batch_size=batch_size,
            )


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
@beartype
def main(
    *,
    file: Path,
    parent_page_id: str,
    title: str,
) -> None:
    """
    Upload documentation to Notion.
    """
    session = Session()

    blocks = json.loads(s=file.read_text(encoding="utf-8"))

    # Workaround for https://github.com/ultimate-notion/ultimate-notion/issues/103
    Page.parent_db = None  # type: ignore[method-assign,assignment] # pyright: ignore[reportAttributeAccessIssue]
    assert Page.parent_db is None

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

    for child in page.children:  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        child.delete()

    # See https://developers.notion.com/reference/request-limits#limits-for-property-values
    # which shows that the max number of blocks per request is 100.
    # Without batching, we get 413 errors.
    notion_blocks_batch_size = 100
    upload_blocks_recursively(
        parent=page,
        block_details_list=blocks,
        session=session,
        batch_size=notion_blocks_batch_size,
    )
    sys.stdout.write(f"Updated existing page: {title} (ID: {page.id})\n")
