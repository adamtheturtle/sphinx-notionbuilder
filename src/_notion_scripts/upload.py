"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from beartype import beartype
from notion_client import Client
from ultimate_notion import Session
from ultimate_notion.blocks import Block, ChildrenMixin
from ultimate_notion.page import Page

_NOTION_BLOCKS_BATCH_SIZE = 100  # Max blocks per request to avoid 413 errors


_Block = dict[str, Any]
_RichTextBlock = dict[str, Any]


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
def _get_block_children(block: _Block) -> list[_Block]:
    """
    Get children from a block, regardless of block type.
    """
    block_type = block.get("type")
    if block_type in {
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
        "toggle",
        "quote",
        "callout",
        "synced_block",
        "column",
    }:
        return list(block.get(block_type, {}).get("children", []))
    if block_type == "table_row":
        return []
    return list(block.get("children", []))


@beartype
def _set_block_children(block: _Block, children: list[_Block]) -> _Block:
    """
    Set children on a block, regardless of block type.
    """
    block_copy = dict(block)
    block_type = block.get("type")
    if block_type in {
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
        "toggle",
        "quote",
        "callout",
        "synced_block",
        "column",
    }:
        if block_type not in block_copy:
            block_copy[block_type] = {}
        block_copy[block_type]["children"] = children
    else:
        block_copy["children"] = children
    return block_copy


@beartype
def _remove_block_children(block: _Block) -> _Block:
    """
    Remove children from a block, regardless of block type.
    """
    block_copy = dict(block)
    block_type = block["type"]
    block_copy[str(object=block_type)].pop("children", None)
    block_copy.pop("children", None)
    return block_copy


@dataclass(slots=True)
class _DeepTask:
    """
    A deferred upload task describing where to attach deeper children.
    """

    path: list[int]
    deep_children: list[_Block]


@beartype
def _extract_deep_children(
    blocks: list[_Block],
) -> tuple[list[_Block], list[_DeepTask]]:
    """Extract children beyond a limited max depth and return them as deferred
    tasks.

    Returns:
        - The list of blocks with children limited to max_depth
        - The list of deep upload tasks (index paths and deferred children)
    """
    max_depth = 1
    processed_blocks: list[_Block] = []
    tasks: list[_DeepTask] = []

    def _walk(block: _Block, depth: int, path: list[int]) -> _Block:
        """
        Recursively walk through the block's children and process them.
        """
        children = _get_block_children(block=block)
        if not children:
            return block

        block_copy = dict(block)
        new_children: list[_Block] = []

        for idx, child in enumerate(iterable=children):
            child_children = _get_block_children(block=child)

            if depth >= max_depth and child_children:
                child_copy = _remove_block_children(block=child)
                new_children.append(child_copy)
                tasks.append(
                    _DeepTask(path=[*path, idx], deep_children=child_children)
                )
            else:
                processed = _walk(
                    block=child, depth=depth + 1, path=[*path, idx]
                )
                if not _get_block_children(block=processed):
                    processed = _remove_block_children(block=processed)
                new_children.append(processed)

        if new_children:
            block_copy = _set_block_children(
                block=block_copy, children=new_children
            )
        else:
            block_copy = _remove_block_children(block=block_copy)

        return block_copy

    for i, blk in enumerate(iterable=blocks):
        processed_blocks.append(_walk(block=blk, depth=0, path=[i]))

    return processed_blocks, tasks


@beartype
def _get_uploaded_block_by_path(
    parent: Page | Block[Any], path: list[int]
) -> Block[Any]:
    """
    Follow an index path through .children to return the uploaded block.
    """
    assert isinstance(parent, ChildrenMixin)
    current: Page | Block[Any] = parent
    for index in path:
        current.reload()
        assert isinstance(current, ChildrenMixin)
        children = list(  # pyright: ignore[reportUnknownVariableType]
            current.children  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        )
        current = children[index]  # pyright: ignore[reportUnknownVariableType]
    return cast("Block[Any]", current)


@beartype
def _upload_blocks_with_deep_nesting(
    notion_client: Client,
    blocks: list[_Block],
    batch_size: int,
    parent: Page | Block[Any],
    session: Session,
) -> None:
    """
    Upload blocks with support for deep nesting by making multiple API calls.
    """
    if not blocks:
        return

    processed_blocks, deep_upload_tasks = _extract_deep_children(blocks=blocks)

    sys.stderr.write("Uploading main blocks...\n")
    _upload_blocks_in_batches(
        notion_client=notion_client,
        parent_id=str(object=parent.id),
        blocks=processed_blocks,
        batch_size=batch_size,
    )

    sys.stderr.write(
        f"Processing {len(deep_upload_tasks)} deep nesting tasks...\n"
    )

    for task in deep_upload_tasks:
        matching_block = _get_uploaded_block_by_path(
            parent=parent, path=task.path
        )
        _upload_blocks_with_deep_nesting(
            notion_client=notion_client,
            blocks=task.deep_children,
            batch_size=batch_size,
            parent=matching_block,
            session=session,
        )


@beartype
def _upload_blocks_in_batches(
    notion_client: Client,
    parent_id: str,
    blocks: list[_Block],
    batch_size: int,
) -> None:
    """
    Upload blocks to a page in batches to avoid 413 errors.
    """
    total_blocks = len(blocks)
    sys.stderr.write(
        f"Uploading {total_blocks} blocks in batches of {batch_size}...\n"
    )

    for i in range(0, total_blocks, batch_size):
        batch = blocks[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_blocks + batch_size - 1) // batch_size

        sys.stderr.write(
            f"Uploading batch {batch_num}/{total_batches} "
            f"({len(batch)} blocks)...\n"
        )

        notion_client.blocks.children.append(
            block_id=parent_id,
            children=batch,
        )

    sys.stderr.write(f"Successfully uploaded all {total_blocks} blocks.\n")


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
    parser.add_argument(
        "--batch-size",
        help="Number of blocks per batch",
        type=int,
        default=_NOTION_BLOCKS_BATCH_SIZE,
    )
    return parser.parse_args()


@beartype
def main() -> None:
    """
    Main entry point for the upload command.
    """
    args = _parse_args()

    notion_client = Client(auth=os.environ["NOTION_TOKEN"])
    session = Session(client=notion_client)
    batch_size = args.batch_size
    title = args.title
    file_path = args.file

    contents = json.loads(s=file_path.read_text(encoding="utf-8"))

    processed_contents = contents

    parent_page = session.get_page(page_ref=args.parent_page_id)
    page = _find_existing_page_by_title(
        parent_page=parent_page, title=args.title
    )

    if not page:
        page = session.create_page(parent=parent_page, title=args.title)
        sys.stdout.write(f"Created new page: {args.title} (ID: {page.id})\n")

    for child in list(  # pyright: ignore[reportUnknownVariableType]
        page.children  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    ):
        child.delete()

    _upload_blocks_with_deep_nesting(
        notion_client=notion_client,
        blocks=processed_contents,
        batch_size=batch_size,
        parent=page,
        session=session,
    )
    sys.stdout.write(f"Updated existing page: {title} (ID: {page.id})\n")


if __name__ == "__main__":
    main()
