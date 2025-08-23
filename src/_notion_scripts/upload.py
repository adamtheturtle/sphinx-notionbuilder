"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from notion_client import Client

NOTION_RICH_TEXT_LIMIT = 2000
NOTION_BLOCKS_BATCH_SIZE = 100  # Max blocks per request to avoid 413 errors


_Block = dict[str, Any]
_RichTextBlock = dict[str, Any]


def _split_rich_text(rich_text: list[_RichTextBlock]) -> list[_RichTextBlock]:
    """
    Given a list of rich_text objects, split any 'text.content' >2000 chars
    into multiple objects, preserving all other fields (annotations, links,
    etc).
    """
    new_rich_text: list[_RichTextBlock] = []
    for obj in rich_text:
        if obj.get("type") == "text" and "content" in obj["text"]:
            content = obj["text"]["content"]
            if len(content) > NOTION_RICH_TEXT_LIMIT:
                # Split content into chunks
                for i in range(0, len(content), NOTION_RICH_TEXT_LIMIT):
                    chunk = content[i : i + NOTION_RICH_TEXT_LIMIT]
                    new_obj = json.loads(s=json.dumps(obj=obj))  # deep copy
                    new_obj["text"]["content"] = chunk
                    new_rich_text.append(new_obj)
            else:
                new_rich_text.append(obj)
        else:
            new_rich_text.append(obj)
    return new_rich_text


def _process_block(block: _Block) -> _Block:
    """
    Recursively process a Notion block dict, splitting any rich_text >2000
    chars.
    """
    block = dict(block)  # shallow copy
    for key, value in block.items():
        if isinstance(value, dict):
            # Check for 'rich_text' key
            if "rich_text" in value and isinstance(value["rich_text"], list):
                rich_text_list = cast(
                    "list[_RichTextBlock]",
                    value["rich_text"],
                )
                value["rich_text"] = _split_rich_text(rich_text=rich_text_list)
            # Recurse into dict
            typed_value = cast("_Block", value)
            block[key] = _process_block(block=typed_value)
        elif isinstance(value, list):
            # Recurse into list elements
            processed_list: list[Any] = []
            for v in value:  # pyright: ignore[reportUnknownVariableType]
                if isinstance(v, dict):
                    typed_v = cast("_Block", v)
                    processed_list.append(_process_block(block=typed_v))
                else:
                    processed_list.append(v)
            block[key] = processed_list
    return block


def _find_existing_page_by_title(
    notion_client: Client,
    parent_page_id: str,
    title: str,
) -> str | None:
    """Find an existing page with the given title in the parent page (top-level
    only).

    Returns the page ID if found, None otherwise.
    """
    children: Any = notion_client.blocks.children.list(block_id=parent_page_id)
    children_results = children.get("results", [])

    for child_block in children_results:
        if (
            child_block.get("type") == "child_page"
            and "child_page" in child_block
        ):
            child_page = child_block["child_page"]
            page_title = child_page.get("title", "")
            if page_title == title:
                return str(object=child_block.get("id"))

    return None


def _upload_blocks_in_batches(
    notion_client: Client,
    page_id: str,
    blocks: list[_Block],
    batch_size: int = NOTION_BLOCKS_BATCH_SIZE,
) -> None:
    """
    Upload blocks to a page in batches to avoid 413 errors.
    """
    if not blocks:
        return

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

        try:
            notion_client.blocks.children.append(
                block_id=page_id,
                children=batch,
            )
        except Exception as e:
            sys.stderr.write(f"Error uploading batch {batch_num}: {e}\n")
            raise

    sys.stderr.write(f"Successfully uploaded all {total_blocks} blocks.\n")


def main() -> None:
    """
    Main entry point for the upload command.
    """
    parser = argparse.ArgumentParser(description="Upload to Notion")
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
        help=(
            f"Number of blocks per batch (default: {NOTION_BLOCKS_BATCH_SIZE})"
        ),
        type=int,
        default=NOTION_BLOCKS_BATCH_SIZE,
    )
    args = parser.parse_args()

    # Initialize Notion client
    notion = Client(auth=os.environ["NOTION_TOKEN"])

    with args.file.open("r", encoding="utf-8") as f:
        contents = json.load(fp=f)

    # Workaround Notion 2k char limit: preprocess contents
    processed_contents = [
        _process_block(block=content_block) for content_block in contents
    ]

    existing_page_id = _find_existing_page_by_title(
        notion_client=notion,
        parent_page_id=args.parent_page_id,
        title=args.title,
    )

    if existing_page_id:
        existing_children: Any = notion.blocks.children.list(
            block_id=existing_page_id,
        )
        child_results = existing_children.get(
            "results",
            [],
        )
        for child in child_results:
            child_id = child.get("id")
            if child_id:
                notion.blocks.delete(block_id=child_id)

        _upload_blocks_in_batches(
            notion_client=notion,
            page_id=existing_page_id,
            blocks=processed_contents,
            batch_size=args.batch_size,
        )
        sys.stdout.write(
            f"Updated existing page: {args.title} (ID: {existing_page_id})"
        )
    else:
        # For new pages, we still need to handle large content
        # Split into initial creation + additional batches if needed
        if len(processed_contents) > args.batch_size:
            # Create page with first batch
            initial_batch = processed_contents[: args.batch_size]
            remaining_blocks = processed_contents[args.batch_size :]

            new_page: Any = notion.pages.create(
                parent={"type": "page_id", "page_id": args.parent_page_id},
                properties={
                    "title": {"title": [{"text": {"content": args.title}}]},
                },
                children=initial_batch,
            )
            page_id = new_page.get("id", "unknown")

            # Upload remaining blocks in batches
            if remaining_blocks:
                _upload_blocks_in_batches(
                    notion_client=notion,
                    page_id=page_id,
                    blocks=remaining_blocks,
                    batch_size=args.batch_size,
                )
        else:
            # Small enough to create in one go
            new_page_small: Any = notion.pages.create(
                parent={"type": "page_id", "page_id": args.parent_page_id},
                properties={
                    "title": {"title": [{"text": {"content": args.title}}]},
                },
                children=processed_contents,
            )
            page_id = new_page_small.get("id", "unknown")

        sys.stdout.write(f"Created new page: {args.title} (ID: {page_id})")


if __name__ == "__main__":
    main()
