"""CLI for uploading documentation to Notion.

Inspired by https://github.com/ftnext/sphinx-notion/blob/main/upload.py.
"""

import json
import logging
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
    PageNotFoundError,
    UploadStrategy,
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
    "--page-id",
    help=(
        "ID of an existing page to update. The page is renamed to the "
        "given title. Without this, the page is matched by title, and "
        "created if no page with the title exists."
    ),
    required=False,
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
    "--strategy",
    type=click.Choice(choices=[strategy.value for strategy in UploadStrategy]),
    default=UploadStrategy.DIFF.value,
    show_default=True,
    help=(
        "Block sync strategy: 'diff' preserves unchanged block IDs and "
        "discussions; 'replace' appends all content before deleting old "
        "blocks."
    ),
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
@cloup.option(
    "--notion-api-base-url",
    help=(
        "Override the Notion API base URL. "
        "Useful for tests against a mock Notion API."
    ),
    required=False,
)
@beartype
def main(
    *,
    file: Path,
    parent_page_id: str | None,
    parent_database_id: str | None,
    title: str,
    page_id: str | None,
    icon: str | None,
    cover_path: Path | None,
    cover_url: str | None,
    strategy: str,
    cancel_on_discussion: bool,
    notion_api_base_url: str | None,
) -> None:
    """Upload documentation to Notion."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    session = (
        Session(base_url=notion_api_base_url)
        if notion_api_base_url is not None
        else Session()
    )
    block_dicts = json.loads(s=file.read_text(encoding="utf-8"))
    blocks = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))
        for details in block_dicts
    ]

    try:
        page = upload_to_notion(
            session=session,
            blocks=blocks,
            page_id=page_id,
            parent_page_id=parent_page_id,
            parent_database_id=parent_database_id,
            title=title,
            icon=icon,
            cover_path=cover_path,
            cover_url=cover_url,
            cancel_on_discussion=cancel_on_discussion,
            strategy=UploadStrategy(value=strategy),
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
    except PageNotFoundError as exc:
        raise click.ClickException(message=str(object=exc)) from None
    finally:
        session.close()

    click.echo(message=f"Uploaded page: '{title}' ({page.url})")
