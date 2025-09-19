"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import json
import sys
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import urlparse
from urllib.request import url2pathname

import click
from beartype import beartype
from ultimate_notion import Emoji, Session
from ultimate_notion.blocks import Block, ChildrenMixin
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock
from ultimate_notion.obj_api.core import Unset, UnsetType


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
def _first_level_block_from_details(
    *,
    details: _SerializedBlockTreeNode,
    session: Session,
) -> Block:
    """Create a Block from a serialized block details.

    Upload any required local files.
    """
    block = Block.wrap_obj_ref(
        UnoObjAPIBlock.model_validate(obj=details["block"])
    )

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


@beartype
def _upload_blocks_recursively(
    parent: ChildrenMixin[Any],
    block_details_list: list[_SerializedBlockTreeNode],
    session: Session,
    batch_size: int,
) -> None:
    """
    Upload blocks recursively, handling the new structure with block and
    children.
    """
    first_level_blocks: list[Block] = [
        _first_level_block_from_details(details=details, session=session)
        for details in block_details_list
    ]

    # See https://github.com/ultimate-notion/ultimate-notion/issues/119
    # for removing this when Ultimate Notion supports batching.
    for block_batch in _batch_list(
        elements=first_level_blocks,
        batch_size=batch_size,
    ):
        parent.append(blocks=block_batch)

    for uploaded_block_index, uploaded_block in enumerate(
        iterable=parent.children
    ):
        block_details = block_details_list[uploaded_block_index]
        if block_details["children"]:
            block_obj = session.get_block(block_ref=uploaded_block.id)
            assert isinstance(block_obj, ChildrenMixin)
            _upload_blocks_recursively(
                parent=block_obj,
                block_details_list=block_details["children"],
                session=session,
                batch_size=batch_size,
            )


@beartype
def _reconstruct_nested_structure(
    *,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Reconstruct nested structure from flattened block items.
    """
    result: list[dict[str, Any]] = []
    for item in items:
        block = item["block"]
        block_type = block["type"]

        # Handle blocks that can have children
        if block_type in {
            "paragraph",
            "callout",
            "bulleted_list_item",
            "numbered_list_item",
            "toggle",
        }:
            pass
            # children = item.get("children", [])
            # nested_blocks = _reconstruct_nested_structure(
            #     items=children,
            # )
            # block[block_type]["children"] = nested_blocks

        result.append(block)
    return result


@beartype
def _sanitize_serialized_block(
    *,
    serialized_block: dict[str, Any],
) -> dict[str, Any]:
    """
    Sanitize a serialized block.
    """
    return serialized_block
    if isinstance(serialized_block, dict):
        return {
            key: _sanitize_serialized_block(serialized_block=value)
            for key, value in serialized_block.items()
        }
    return serialized_block


@beartype
def _sanitize_block(
    *,
    block: Block,
    session: Session,
) -> Any:
    """
    Sanitize a block.
    """
    if block.obj_ref.id and not isinstance(block.obj_ref.id, UnsetType):
        block = session.get_block(block_ref=block.obj_ref.id)
    block.obj_ref.created_by = Unset
    block.obj_ref.last_edited_by = Unset
    block.obj_ref.created_time = Unset
    block.obj_ref.last_edited_time = Unset
    block.obj_ref.id = Unset
    block.obj_ref.parent = Unset
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
    block_list = _reconstruct_nested_structure(items=blocks)
    block_obj_list = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=block))
        for block in block_list
    ]
    sanitized_block_list = [
        _sanitize_block(block=block, session=session)
        for block in block_obj_list
    ]
    children_list = list(page.children)
    sanitized_children_list = [
        _sanitize_block(block=child, session=session)
        for child in children_list
    ]

    import difflib
    import pprint

    for index, page_child in enumerate(sanitized_children_list):
        block_child = sanitized_block_list[index]
        if page_child != block_child:
            s1 = pprint.pformat(
                page_child.__dict__, sort_dicts=True
            ).splitlines()
            s2 = pprint.pformat(
                block_child.__dict__, sort_dicts=True
            ).splitlines()

            diff = difflib.unified_diff(s1, s2)

            diff_list = list(diff)
            nice_diff = "\n".join(diff)
            breakpoint()
    # children_obj_list = [
    #     Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=child))
    #     for child in children_list
    # ]
    # serialized_children_list = [
    #     child.obj_ref.serialize_for_api() for child in children_list
    # ]
    # sanitized_serialized_children_list = [
    #     _sanitize_serialized_block(serialized_block=serialized_block)
    #     for serialized_block in serialized_children_list
    # ]
    breakpoint()
    # for child in page.children:
    #     child.delete()

    # See https://developers.notion.com/reference/request-limits#limits-for-property-values
    # which shows that the max number of blocks per request is 100.
    # Without batching, we get 413 errors.
    notion_blocks_batch_size = 100
    _upload_blocks_recursively(
        parent=page,
        block_details_list=blocks,
        session=session,
        batch_size=notion_blocks_batch_size,
    )
    sys.stdout.write(f"Updated existing page: {title} (ID: {page.id})\n")
