"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from beartype import beartype
from ultimate_notion import Session
from ultimate_notion.blocks import Block, ChildrenMixin
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock
from ultimate_notion.page import Page


@beartype
def _batch_list[T](elements: list[T], batch_size: int) -> list[list[T]]:
    """
    Split a list into batches of a given size.
    """
    return [
        elements[start_index : start_index + batch_size]
        for start_index in range(0, len(elements), batch_size)
    ]


@beartype
def _find_existing_page_by_title(parent_page: Page, title: str) -> Page | None:
    """Find an existing page with the given title in the parent page (top-level
    only).

    Return the page if found, otherwise None.
    """
    for child_page in parent_page.subpages:
        if str(object=child_page.title) == title:
            return child_page
    return None


@beartype
def _parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the upload script.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Upload to Notion",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="JSON File to upload",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-p",
        "--parent_page_id",
        help="Parent page ID (integration connected)",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--title",
        help="Title of the new page",
        required=True,
    )
    return parser.parse_args()


@beartype
def upload_blocks_recursively(
    parent: Page | ChildrenMixin[Any],
    block_details_list: list[dict[str, Any]],
    session: Session,
    batch_size: int,
) -> None:
    """
    Upload blocks recursively, handling the new structure with block and
    children.
    """
    # Upload this level's blocks in batches
    children_block_api_objs = [
        UnoObjAPIBlock.model_validate(obj=details["block"])
        for details in block_details_list
    ]
    children_block_objs: list[Block[Any]] = [
        Block.wrap_obj_ref(block_api_obj)  # pyright: ignore[reportUnknownMemberType]
        for block_api_obj in children_block_api_objs
    ]
    children_block_batches = _batch_list(
        elements=children_block_objs,
        batch_size=batch_size,
    )
    for children_block_batch in children_block_batches:
        parent.append(blocks=children_block_batch)  # pyright: ignore[reportUnknownMemberType]

    uploaded_blocks = parent.children  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    for i, block in enumerate(iterable=uploaded_blocks):  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        block_details = block_details_list[i]
        if block_details["children"]:
            block_obj = session.get_block(block_ref=block.id)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            assert isinstance(block_obj, ChildrenMixin)
            upload_blocks_recursively(
                parent=block_obj,
                block_details_list=block_details["children"],
                session=session,
                batch_size=batch_size,
            )


@beartype
def main() -> None:
    """
    Main entry point for the upload command.
    """
    args = _parse_args()

    session = Session()
    title = args.title
    file_path = args.file
    parent_page_id = args.parent_page_id

    blocks = json.loads(s=file_path.read_text(encoding="utf-8"))

    # Workaround for https://github.com/ultimate-notion/ultimate-notion/issues/103
    Page.parent_db = None  # type: ignore[method-assign,assignment] # pyright: ignore[reportAttributeAccessIssue]
    assert Page.parent_db is None

    parent_page = session.get_page(page_ref=parent_page_id)
    page = _find_existing_page_by_title(parent_page=parent_page, title=title)

    if not page:
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


if __name__ == "__main__":
    main()
