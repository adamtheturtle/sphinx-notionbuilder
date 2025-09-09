"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import json
import sys
from pathlib import Path
from typing import Any, NotRequired, Required, TypedDict

import click
from beartype import beartype
from ultimate_notion import Session
from ultimate_notion.blocks import Block, ChildrenMixin
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock


class _SerializedBlockTreeNode(TypedDict):
    """
    A node in the block tree representing a Notion block with its children.
    """

    block: Required[dict[str, Any]]
    children: Required[list["_SerializedBlockTreeNode"]]
    file_to_upload: NotRequired[str]


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
def _process_local_files(
    *,
    block_details_list: list[_SerializedBlockTreeNode],
    session: Session,
    source_dir: Path,
) -> None:
    """Process local files in the block details and upload them to Notion.

    This modifies the block_details_list in place, replacing local file
    references with uploaded file references.
    """
    for block_details in block_details_list:
        # Check if this block has a file to upload
        if "file_to_upload" in block_details:
            file_path = block_details["file_to_upload"]
            # Resolve the file path relative to the source directory
            full_path = source_dir / file_path
            # Upload the file to Notion
            with full_path.open(mode="rb") as f:
                uploaded_file = session.upload(
                    file=f,
                    file_name=full_path.name,
                )

            # Wait for the upload to complete
            uploaded_file.wait_until_uploaded()
            # Create a new Ultimate Notion Image block with the uploaded
            # file.
            # This will replace the entire block structure
            new_image_block = UnoImage(
                file=uploaded_file,
                caption=None,
            )
            # Replace the entire block with the new one
            block_details["block"] = (
                new_image_block.obj_ref.serialize_for_api()
            )
            # Remove the file_to_upload field since it's been processed
            del block_details["file_to_upload"]

        # Recursively process children
        if block_details["children"]:
            _process_local_files(
                block_details_list=block_details["children"],
                session=session,
                source_dir=source_dir,
            )


@beartype
def _first_level_block_from_details(
    *,
    details: _SerializedBlockTreeNode,
) -> Block:
    """
    Create a Block from a serialized block details.
    """
    return Block.wrap_obj_ref(
        UnoObjAPIBlock.model_validate(obj=details["block"])
    )


@beartype
def upload_blocks_recursively(
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
        _first_level_block_from_details(details=details)
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
@click.option(
    "--source-dir",
    help="Source directory for resolving local file paths",
    type=click.Path(
        exists=True,
        path_type=Path,
        file_okay=False,
        dir_okay=True,
    ),
)
@beartype
def main(
    *,
    file: Path,
    parent_page_id: str,
    title: str,
    source_dir: Path | None = None,
) -> None:
    """
    Upload documentation to Notion.
    """
    session = Session()

    blocks = json.loads(s=file.read_text(encoding="utf-8"))

    # Process local files if source directory is provided
    if source_dir is not None:
        _process_local_files(
            block_details_list=blocks,
            session=session,
            source_dir=source_dir,
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
