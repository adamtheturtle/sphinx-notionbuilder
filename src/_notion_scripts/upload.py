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
from ultimate_notion.blocks import Block, ChildrenMixin
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

    serialized_children = details[block.obj_ref.type].get("children", [])
    for child in serialized_children:
        child_block = _block_from_details(details=child, session=session)
        assert isinstance(block, ChildrenMixin)
        block.append(blocks=[child_block])

    return block


@beartype
def _serialize_block_with_children(
    *,
    block: Block,
) -> dict[str, Any]:
    """
    Serialize a block with its children.
    """
    serialized_obj = block.obj_ref.serialize_for_api()
    if isinstance(block, ChildrenMixin) and block.children:
        serialized_obj[block.obj_ref.type]["children"] = [
            _serialize_block_with_children(block=child)
            for child in block.children
        ]
    return serialized_obj


@beartype
def _deserialize_block_with_children(
    *,
    details: dict[str, Any],
) -> Block:
    """
    Deserialize a block with its children.
    """
    block = Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))

    return block
    serialized_children = details[block.obj_ref.type].get("children", [])
    for child in serialized_children:
        child_block = _deserialize_block_with_children(details=child)
        assert isinstance(block, ChildrenMixin)
        block.append(blocks=[child_block])

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

    block_child_serialized_with_children = {
        "object": "block",
        "has_children": True,
        "in_trash": False,
        "archived": False,
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {
                    "type": "text",
                    "plain_text": "A",
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                    },
                    "text": {"content": "A"},
                }
            ],
            "color": "default",
            "children": [
                {
                    "object": "block",
                    "has_children": False,
                    "in_trash": False,
                    "archived": False,
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "plain_text": "B",
                                "annotations": {
                                    "bold": False,
                                    "italic": False,
                                    "strikethrough": False,
                                    "underline": False,
                                    "code": False,
                                },
                                "text": {"content": "B"},
                            }
                        ],
                        "color": "default",
                        "children": [],
                    },
                }
            ],
        },
    }

    block_child = Block.wrap_obj_ref(
        UnoObjAPIBlock.model_validate(obj=block_child_serialized_with_children)
    )

    another_block_child = Block.wrap_obj_ref(
        UnoObjAPIBlock.model_validate(obj=block_child_serialized_with_children)
    )

    assert block_child == another_block_child

    page.append(blocks=[block_child])

    page.reload()
    assert len(page.children) == 1
    assert page.children[0] == block_child

    # This hits an assertion error
    assert page.children[0] == another_block_child

    sys.exit()
    import difflib
    import pprint

    for index, page_child in enumerate(iterable=page.children):
        print("Comparing index", index)
        block_child = _deserialize_block_with_children(details=blocks[index])
        if page_child != block_child:
            page_child_serialized_with_children = (
                _serialize_block_with_children(block=page_child)
            )
            block_child_serialized_with_children = (
                _serialize_block_with_children(block=block_child)
            )
            s1 = pprint.pformat(
                object=page_child_serialized_with_children, sort_dicts=True
            ).splitlines()
            s2 = pprint.pformat(
                object=block_child_serialized_with_children, sort_dicts=True
            ).splitlines()

            diff = difflib.unified_diff(a=s1, b=s2, n=20)

            diff_list = list(diff)
            print("Item at index", index, "is different")
            nice_diff = "\n".join(diff_list)
            breakpoint()

    breakpoint()

    for child in page.children:
        child.delete()

    block_objs = [
        _block_from_details(details=details, session=session)
        for details in blocks
    ]
    page.append(blocks=block_objs)
    sys.stdout.write(f"Updated existing page: {title} (ID: {page.id})\n")
