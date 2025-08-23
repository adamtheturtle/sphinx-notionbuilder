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


def _get_block_children(block: _Block) -> list[_Block]:
    """
    Get children from a block, regardless of block type.
    """
    block_type = block.get("type")
    if block_type == "bulleted_list_item":
        return list(block.get("bulleted_list_item", {}).get("children", []))
    if block_type == "numbered_list_item":
        return list(block.get("numbered_list_item", {}).get("children", []))
    if block_type == "to_do":
        return list(block.get("to_do", {}).get("children", []))
    if block_type == "toggle":
        return list(block.get("toggle", {}).get("children", []))
    if block_type == "quote":
        return list(block.get("quote", {}).get("children", []))
    if block_type == "callout":
        return list(block.get("callout", {}).get("children", []))
    if block_type == "synced_block":
        return list(block.get("synced_block", {}).get("children", []))
    if block_type == "column":
        return list(block.get("column", {}).get("children", []))
    if block_type == "table_row":
        return []  # Table rows don't have nested children in the same way
    # Generic case - many block types store children at the top level
    return list(block.get("children", []))


def _set_block_children(block: _Block, children: list[_Block]) -> _Block:
    """
    Set children on a block, regardless of block type.
    """
    block_copy = dict(block)
    block_type = block.get("type")

    if block_type == "bulleted_list_item":
        if "bulleted_list_item" not in block_copy:
            block_copy["bulleted_list_item"] = {}
        block_copy["bulleted_list_item"]["children"] = children
    elif block_type == "numbered_list_item":
        if "numbered_list_item" not in block_copy:
            block_copy["numbered_list_item"] = {}
        block_copy["numbered_list_item"]["children"] = children
    elif block_type == "to_do":
        if "to_do" not in block_copy:
            block_copy["to_do"] = {}
        block_copy["to_do"]["children"] = children
    elif block_type == "toggle":
        if "toggle" not in block_copy:
            block_copy["toggle"] = {}
        block_copy["toggle"]["children"] = children
    elif block_type == "quote":
        if "quote" not in block_copy:
            block_copy["quote"] = {}
        block_copy["quote"]["children"] = children
    elif block_type == "callout":
        if "callout" not in block_copy:
            block_copy["callout"] = {}
        block_copy["callout"]["children"] = children
    elif block_type == "synced_block":
        if "synced_block" not in block_copy:
            block_copy["synced_block"] = {}
        block_copy["synced_block"]["children"] = children
    elif block_type == "column":
        if "column" not in block_copy:
            block_copy["column"] = {}
        block_copy["column"]["children"] = children
    else:
        # Generic case
        block_copy["children"] = children

    return block_copy


def _remove_block_children(block: _Block) -> _Block:
    """
    Remove children from a block, regardless of block type.
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
        if block_type in block_copy:
            block_copy[block_type].pop("children", None)
    else:
        block_copy.pop("children", None)

    return block_copy


def _get_block_content(block: _Block) -> str:
    """
    Get text content from a block for matching purposes.
    """
    block_type = block.get("type")

    # Most block types store rich_text in their type-specific object
    if block_type in [
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
        "toggle",
        "quote",
        "heading_1",
        "heading_2",
        "heading_3",
        "paragraph",
    ]:
        type_obj = block.get(block_type, {})
        rich_text = type_obj.get("rich_text", [])
        return "".join(item.get("plain_text", "") for item in rich_text)
    if block_type == "callout":
        rich_text = block.get("callout", {}).get("rich_text", [])
        return "".join(item.get("plain_text", "") for item in rich_text)
    if block_type == "code":
        rich_text = block.get("code", {}).get("rich_text", [])
        return "".join(item.get("plain_text", "") for item in rich_text)
    # For other block types, try to find any text content
    # This is a fallback for block types we haven't specifically handled
    return str(object=block.get("id", ""))


def _extract_deep_children(
    blocks: list[_Block],
    max_depth: int = 1,
) -> tuple[list[_Block], list[tuple[_Block, list[_Block]]]]:
    """Extract children beyond max_depth and return them separately.

    Returns:
        - List of blocks with children limited to max_depth
        - List of (parent_block, deep_children) pairs for uploading later
    """
    processed_blocks = []
    deep_upload_tasks = []

    def process_block(block: _Block, current_depth: int = 0) -> _Block:
        children = _get_block_children(block=block)
        if not children:
            return block

        block_copy = dict(block)
        processed_children = []

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
                processed_child = process_block(
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
        processed_block = process_block(block=block, current_depth=0)
        processed_blocks.append(processed_block)

    return processed_blocks, deep_upload_tasks


def _get_all_uploaded_blocks_recursively(
    notion_client: Client,
    parent_id: str,
) -> list[_Block]:
    """
    Recursively fetch all uploaded blocks and their children.
    """
    all_blocks = []

    # Get immediate children
    page_children: Any = notion_client.blocks.children.list(
        block_id=parent_id,
        page_size=100,
    )
    immediate_blocks = page_children.get("results", [])

    for block in immediate_blocks:
        all_blocks.append(block)

        # If this block has children, fetch them recursively
        if block.get("has_children", False):
            child_blocks = _get_all_uploaded_blocks_recursively(
                notion_client=notion_client, parent_id=block["id"]
            )
            all_blocks.extend(child_blocks)

    return all_blocks


def _upload_blocks_with_deep_nesting(
    notion_client: Client,
    page_id: str,
    blocks: list[_Block],
    batch_size: int = NOTION_BLOCKS_BATCH_SIZE,
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

    # Now handle deep children by finding their uploaded parents
    if deep_upload_tasks:
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
                template_block=parent_template, uploaded_blocks=uploaded_blocks
            )

            assert matching_block_id is not None
            _upload_blocks_with_deep_nesting(
                notion_client=notion_client,
                page_id=matching_block_id,
                blocks=deep_children,
                batch_size=batch_size,
            )


def _find_matching_block_id(
    template_block: _Block,
    uploaded_blocks: list[_Block],
) -> str | None:
    """Find the ID of an uploaded block that matches the template block.

    Searches recursively through all uploaded blocks and their children.
    """
    template_type = template_block.get("type")
    if not template_type:
        return None

    def search_blocks_recursively(blocks: list[_Block]) -> str | None:
        for uploaded_block in blocks:
            # Check if this block matches
            if _blocks_match(
                template_block=template_block, uploaded_block=uploaded_block
            ):
                return uploaded_block.get("id")

            # Check children if they exist
            if uploaded_block.get("has_children", False):
                # Note: We'd need to fetch children here, but for now
                # let's assume children are included in the response
                children = uploaded_block.get("children", [])
                if children:
                    child_result = search_blocks_recursively(blocks=children)
                    if child_result:
                        return child_result
        return None

    return search_blocks_recursively(blocks=uploaded_blocks)


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

        _upload_blocks_with_deep_nesting(
            notion_client=notion,
            page_id=existing_page_id,
            blocks=processed_contents,
            batch_size=args.batch_size,
        )
        sys.stdout.write(
            f"Updated existing page: {args.title} (ID: {existing_page_id})"
        )
    else:
        # For new pages, we need to handle deep nesting
        if len(processed_contents) > args.batch_size:
            # Create page with first batch (but limit nesting)
            initial_batch, deep_tasks = _extract_deep_children(
                blocks=processed_contents[: args.batch_size], max_depth=1
            )
            remaining_blocks = processed_contents[args.batch_size :]

            new_page: Any = notion.pages.create(
                parent={"type": "page_id", "page_id": args.parent_page_id},
                properties={
                    "title": {"title": [{"text": {"content": args.title}}]},
                },
                children=initial_batch,
            )
            page_id = new_page.get("id", "unknown")

            # Handle deep children from initial batch
            if deep_tasks:
                sys.stderr.write(
                    "Processing deep children from initial batch...\n"
                )
                page_children: Any = notion.blocks.children.list(
                    block_id=page_id, page_size=100
                )
                uploaded_blocks = page_children.get("results", [])

                for parent_template, deep_children in deep_tasks:
                    matching_block_id = _find_matching_block_id(
                        template_block=parent_template,
                        uploaded_blocks=uploaded_blocks,
                    )
                    if matching_block_id:
                        _upload_blocks_with_deep_nesting(
                            notion_client=notion,
                            page_id=matching_block_id,
                            blocks=deep_children,
                            batch_size=args.batch_size,
                        )

            # Upload remaining blocks in batches
            if remaining_blocks:
                _upload_blocks_with_deep_nesting(
                    notion_client=notion,
                    page_id=page_id,
                    blocks=remaining_blocks,
                    batch_size=args.batch_size,
                )
            sys.stdout.write(f"Created new page: {args.title} (ID: {page_id})")
            sys.exit(0)

        # Small enough to create in one go, but still handle deep nesting
        main_blocks, deep_tasks = _extract_deep_children(
            blocks=processed_contents, max_depth=1
        )

        new_page_small: Any = notion.pages.create(
            parent={"type": "page_id", "page_id": args.parent_page_id},
            properties={
                "title": {"title": [{"text": {"content": args.title}}]},
            },
            children=main_blocks,
        )
        page_id = new_page_small.get("id", "unknown")

        # Handle deep children
        if deep_tasks:
            sys.stderr.write("Processing deep children...\n")
            page_children_2: Any = notion.blocks.children.list(
                block_id=page_id, page_size=100
            )
            uploaded_blocks_2 = page_children_2.get("results", [])

            for parent_template, deep_children in deep_tasks:
                matching_block_id = _find_matching_block_id(
                    template_block=parent_template,
                    uploaded_blocks=uploaded_blocks_2,
                )
                if matching_block_id:
                    _upload_blocks_with_deep_nesting(
                        notion_client=notion,
                        page_id=matching_block_id,
                        blocks=deep_children,
                        batch_size=args.batch_size,
                    )

        sys.stdout.write(f"Created new page: {args.title} (ID: {page_id})")


if __name__ == "__main__":
    main()
