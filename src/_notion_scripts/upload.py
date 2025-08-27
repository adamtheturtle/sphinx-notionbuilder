"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from beartype import beartype
from notion_client import Client
from ultimate_notion import Session
from ultimate_notion.page import Page

_NOTION_BLOCKS_BATCH_SIZE = 100  # Max blocks per request to avoid 413 errors


_Block = dict[str, Any]


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
def upload_blocks_recursively(
    parent_id: str,
    block_details_list: list[dict[str, Any]],
    notion_client: Client,
    batch_size: int,
) -> None:
    """
    Upload blocks recursively, handling the new structure with block and
    children.
    """
    if not block_details_list:
        return

    # Extract just the blocks for this level
    level_blocks = [details["block"] for details in block_details_list]

    # Upload this level's blocks in batches
    _upload_blocks_in_batches(
        notion_client=notion_client,
        parent_id=parent_id,
        blocks=level_blocks,
        batch_size=batch_size,
    )

    # Get the uploaded blocks to get their IDs for children
    uploaded_blocks: dict[str, Any] = notion_client.blocks.children.list(  # type: ignore[assignment] # pyright: ignore[reportAssignmentType]
        block_id=parent_id
    )
    block_id_map: dict[str, list[dict[str, Any]]] = {}

    # Map the uploaded blocks to their details for children processing
    results = uploaded_blocks.get("results", [])
    for i, block in enumerate(iterable=results):
        if i < len(block_details_list):
            block_details = block_details_list[i]
            if block_details["children"]:
                block_id = block.get("id")
                if block_id:
                    block_id_map[str(object=block_id)] = block_details[
                        "children"
                    ]

    # Recursively upload children for each block that has them
    for block_id, children in block_id_map.items():
        upload_blocks_recursively(
            parent_id=block_id,
            block_details_list=children,
            notion_client=notion_client,
            batch_size=batch_size,
        )


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

    blocks = json.loads(s=file_path.read_text(encoding="utf-8"))

    # Workaround for https://github.com/ultimate-notion/ultimate-notion/issues/103
    Page.parent_db = None  # type: ignore[method-assign,assignment] # pyright: ignore[reportAttributeAccessIssue]
    assert Page.parent_db is None

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

    # Start the recursive upload process
    upload_blocks_recursively(
        parent_id=str(object=page.id),
        block_details_list=blocks,
        notion_client=notion_client,
        batch_size=batch_size,
    )
    sys.stdout.write(f"Updated existing page: {title} (ID: {page.id})\n")


if __name__ == "__main__":
    main()
