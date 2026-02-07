"""Upload documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import json
from pathlib import Path

import click
import cloup
from beartype import beartype
from ultimate_notion import Session
from ultimate_notion.blocks import Block
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock

from sphinx_notion._upload import (
    DiscussionsExistError,
    PageHasDatabasesError,
    PageHasSubpagesError,
    upload_to_notion,
)


@cloup.command()
@cloup.option(
    "--file",
    help="JSON File to upload",
    required=True,
    type=cloup.Path(
        exists=True,
        path_type=Path,
        file_okay=True,
        dir_okay=False,
    ),
)
@cloup.option_group(
    "Parent location",
    cloup.option(
        "--parent-page-id",
        help="Parent page ID (integration connected)",
    ),
    cloup.option(
        "--parent-database-id",
        help="Parent database ID (integration connected)",
    ),
    constraint=cloup.constraints.RequireExactly(n=1),
)
@cloup.option(
    "--title",
    help="Title of the page to update (or create if it does not exist)",
    required=True,
)
@cloup.option(
    "--icon",
    help="Icon of the page",
    required=False,
)
@cloup.option_group(
    "Cover image",
    cloup.option(
        "--cover-path",
        help="Cover image file path for the page",
        required=False,
        type=cloup.Path(
            exists=True,
            path_type=Path,
            file_okay=True,
            dir_okay=False,
        ),
    ),
    cloup.option(
        "--cover-url",
        help="Cover image URL for the page",
        required=False,
    ),
    constraint=cloup.constraints.mutually_exclusive,
)
@cloup.option(
    "--cancel-on-discussion",
    help=(
        "Cancel upload with error if blocks to be deleted have discussion "
        "threads"
    ),
    is_flag=True,
    default=False,
)
@beartype
def main(
    *,
    file: Path,
    parent_page_id: str | None,
    parent_database_id: str | None,
    title: str,
    icon: str | None,
    cover_path: Path | None,
    cover_url: str | None,
    cancel_on_discussion: bool,
) -> None:
    """Upload documentation to Notion."""
    session = Session()
    block_dicts = json.loads(s=file.read_text(encoding="utf-8"))
    # See https://github.com/ultimate-notion/ultimate-notion/issues/177
    blocks = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))  # ty: ignore[invalid-argument-type]
        for details in block_dicts
    ]

    try:
        page = upload_to_notion(
            session=session,
            blocks=blocks,
            parent_page_id=parent_page_id,
            parent_database_id=parent_database_id,
            title=title,
            icon=icon,
            cover_path=cover_path,
            cover_url=cover_url,
            cancel_on_discussion=cancel_on_discussion,
        )
    except PageHasSubpagesError:
        error_message = (
            "We only support pages which only contain Blocks. "
            "This page has subpages."
        )
        raise click.ClickException(message=error_message) from None
    except PageHasDatabasesError:
        error_message = (
            "We only support pages which only contain Blocks. "
            "This page has databases."
        )
        raise click.ClickException(message=error_message) from None
    except DiscussionsExistError as exc:
        raise click.ClickException(message=str(object=exc)) from None

    click.echo(message=f"Uploaded page: '{title}' ({page.url})")
