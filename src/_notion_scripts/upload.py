"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from beartype import beartype
from notion_client import Client
from ultimate_notion import Session
from ultimate_notion.page import Page

_NOTION_RICH_TEXT_LIMIT = 2000
_NOTION_BLOCKS_BATCH_SIZE = 100  # Max blocks per request to avoid 413 errors


_Block = dict[str, Any]
_RichTextBlock = dict[str, Any]


@beartype
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
            if len(content) > _NOTION_RICH_TEXT_LIMIT:
                # Split content into chunks
                for i in range(0, len(content), _NOTION_RICH_TEXT_LIMIT):
                    chunk = content[i : i + _NOTION_RICH_TEXT_LIMIT]
                    new_obj = json.loads(s=json.dumps(obj=obj))  # deep copy
                    new_obj["text"]["content"] = chunk
                    new_rich_text.append(new_obj)
            else:
                new_rich_text.append(obj)
        else:
            new_rich_text.append(obj)
    return new_rich_text


@beartype
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


@beartype
def _find_existing_page_by_title(
    parent_page: Page,
    title: str,
) -> Page | None:
    """Find an existing page with the given title in the parent page (top-level
    only).

    Returns the page ID if found, None otherwise.
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
        return []  # Table rows don't have nested children in the same way
    # Generic case - many block types store children at the top level
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
        # Generic case
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


@beartype
def _get_block_content(block: _Block) -> str:
    """
    Get text content from a block for matching purposes.
    """
    block_type = block["type"]
    type_obj = block[str(object=block_type)]
    rich_text = type_obj.get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in rich_text)


@beartype
def _extract_deep_children(
    blocks: list[_Block],
    max_depth: int = 1,
) -> tuple[list[_Block], list[tuple[_Block, list[_Block]]]]:
    """Extract children beyond max_depth and return them separately.

    Returns:
        - List of blocks with children limited to max_depth
        - List of (parent_block, deep_children) pairs for uploading later
    """
    processed_blocks: list[dict[str, Any]] = []
    deep_upload_tasks: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []

    def _process_block(block: _Block, current_depth: int = 0) -> _Block:
        """
        Process a block and its children, limiting the depth of processing.
        """
        children = _get_block_children(block=block)
        if not children:
            return block

        block_copy = dict(block)
        processed_children: list[dict[str, Any]] = []

        for child in children:
            child_children = _get_block_children(block=child)

            if current_depth >= max_depth and child_children:
                # Extract deep children - remove them from this level
                child_copy = _remove_block_children(block=child)
                processed_children.append(child_copy)

                # Store for later upload (we'll find the actual ID later)
                deep_upload_tasks.append((child_copy, child_children))
            else:
                # Keep processing normally, but check for children
                processed_child = _process_block(
                    block=child, current_depth=current_depth + 1
                )
                # Remove empty children arrays
                child_children_after = _get_block_children(
                    block=processed_child
                )
                if not child_children_after:
                    processed_child = _remove_block_children(
                        block=processed_child
                    )
                processed_children.append(processed_child)

        # Update children in the block
        if processed_children:
            block_copy = _set_block_children(
                block=block_copy, children=processed_children
            )
        else:
            block_copy = _remove_block_children(block=block_copy)

        return block_copy

    for block in blocks:
        processed_block = _process_block(block=block, current_depth=0)
        processed_blocks.append(processed_block)

    return processed_blocks, deep_upload_tasks


@beartype
def _get_all_uploaded_blocks_recursively(
    notion_client: Client,
    parent_id: str,
) -> list[_Block]:
    """
    Recursively fetch all uploaded blocks and their children.
    """
    all_blocks: list[Any] = []

    # Get immediate children
    page_children: Any = notion_client.blocks.children.list(
        block_id=parent_id,
        page_size=100,
    )
    immediate_blocks = page_children.get("results", [])

    for block in immediate_blocks:
        all_blocks.append(block)

        # If this block has children, fetch them recursively
        if block["has_children"]:
            child_blocks = _get_all_uploaded_blocks_recursively(
                notion_client=notion_client,
                parent_id=block["id"],
            )
            all_blocks.extend(child_blocks)

    return all_blocks


@beartype
def _upload_blocks_with_deep_nesting(
    notion_client: Client,
    page_id: str,
    blocks: list[_Block],
    batch_size: int,
) -> None:
    """
    Upload blocks with support for deep nesting by making multiple API calls.
    """
    if not blocks:
        return

    # Extract deep children from all blocks
    processed_blocks, deep_upload_tasks = _extract_deep_children(blocks=blocks)

    # Upload the main blocks first (with max 2 levels of nesting)
    sys.stderr.write("Uploading main blocks...\n")
    _upload_blocks_in_batches(
        notion_client=notion_client,
        page_id=page_id,
        blocks=processed_blocks,
        batch_size=batch_size,
    )

    sys.stderr.write(
        f"Processing {len(deep_upload_tasks)} deep nesting tasks...\n"
    )

    # Get all uploaded blocks recursively to find IDs
    uploaded_blocks = _get_all_uploaded_blocks_recursively(
        notion_client=notion_client, parent_id=page_id
    )

    # Process deep upload tasks
    for parent_template, deep_children in deep_upload_tasks:
        # Find the matching uploaded block by comparing content
        matching_block_id = _find_matching_block_id(
            template_block=parent_template,
            uploaded_blocks=uploaded_blocks,
        )

        _upload_blocks_with_deep_nesting(
            notion_client=notion_client,
            page_id=matching_block_id,
            blocks=deep_children,
            batch_size=batch_size,
        )


@beartype
def _find_matching_block_id(
    template_block: _Block,
    uploaded_blocks: list[_Block],
) -> str:
    """
    Find the ID of an uploaded block that matches the template block.
    """
    for uploaded_block in uploaded_blocks:
        # Check if this block matches
        if _blocks_match(
            template_block=template_block, uploaded_block=uploaded_block
        ):
            return str(object=uploaded_block["id"])

    msg = "No matching block found"
    raise ValueError(msg)


@beartype
def _blocks_match(template_block: _Block, uploaded_block: _Block) -> bool:
    """
    Check if a template block matches an uploaded block.
    """
    template_type = template_block.get("type")
    uploaded_type = uploaded_block.get("type")

    if template_type != uploaded_type:
        return False

    # Match by content for all block types that have text content
    template_content = _get_block_content(block=template_block)
    uploaded_content = _get_block_content(block=uploaded_block)

    return template_content == uploaded_content


@beartype
def _upload_blocks_in_batches(
    notion_client: Client,
    page_id: str,
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
            block_id=page_id,
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

    # Load and preprocess contents from the provided JSON file
    contents = json.loads(s=file_path.read_text(encoding="utf-8"))
    # Workaround Notion 2k char limit: preprocess contents
    processed_contents = [
        _process_block(block=content_block) for content_block in contents
    ]

    parent_page = session.get_page(page_ref=args.parent_page_id)
    page = _find_existing_page_by_title(
        parent_page=parent_page,
        title=args.title,
    )

    if not page:
        page = session.create_page(parent=parent_page, title=args.title)
        sys.stdout.write(f"Created new page: {args.title} (ID: {page.id})\n")

    for child in list(page.children):  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType, reportUnknownArgumentType]
        child.delete()

    _upload_blocks_with_deep_nesting(
        notion_client=notion_client,
        page_id=str(object=page.id),
        blocks=processed_contents,
        batch_size=batch_size,
    )
    sys.stdout.write(f"Updated existing page: {title} (ID: {page.id})\n")


if __name__ == "__main__":
    main()
