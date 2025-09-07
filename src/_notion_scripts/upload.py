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


class _SerializedBlockTreeNode(TypedDict):
    """
    A node in the block tree representing a Notion block with its children.
    """

    block: dict[str, Any]
    children: list["_SerializedBlockTreeNode"]


type _BatchedBlockStructure = list[list[_SerializedBlockTreeNode]]


@beartype
def upload_blocks_recursively(
    parent: ChildrenMixin[Any],
    block_details_list: list[_SerializedBlockTreeNode],
    session: Session,
) -> None:
    """Upload blocks recursively, handling the new structure with block and
    children.

    The blocks are already batched by the JSON generation.
    """
    first_level_blocks: list[Block] = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details["block"]))
        for details in block_details_list
    ]
    parent.append(blocks=first_level_blocks)

    for uploaded_block_index, uploaded_block in enumerate(
        iterable=parent.children
    ):
        block_details = block_details_list[uploaded_block_index]
        if block_details["children"]:
            block_obj = session.get_block(block_ref=uploaded_block.id)
            assert isinstance(block_obj, ChildrenMixin)
            upload_blocks_recursively(
                parent=block_obj,
                block_details_list=block_details["children"],
                session=session,
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

    batched_structure: _BatchedBlockStructure = json.loads(
        s=file.read_text(encoding="utf-8")
    )

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

    for child in page.children:
        child.delete()

    for batch in batched_structure:
        upload_blocks_recursively(
            parent=page,
            block_details_list=batch,
            session=session,
        )
    sys.stdout.write(f"Updated existing page: {title} (ID: {page.id})\n")
