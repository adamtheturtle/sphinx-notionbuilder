"""CLI for uploading documentation to Notion."""

import json
from pathlib import Path

import click
import cloup
from beartype import beartype

from sphinx_notion.upload import (
    NotionUploadError,
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
    blocks = json.loads(s=file.read_text(encoding="utf-8"))

    try:
        result = upload_to_notion(
            blocks=blocks,
            parent_page_id=parent_page_id,
            parent_database_id=parent_database_id,
            title=title,
            icon=icon,
            cover_url=cover_url,
            cover_path=cover_path,
            cancel_on_discussion=cancel_on_discussion,
        )
    except NotionUploadError as e:
        raise click.ClickException(message=str(object=e)) from e

    if result.created_new_page:
        click.echo(message=f"Created new page: '{title}' ({result.page_url})")
    else:
        click.echo(
            message=f"Updated existing page: '{title}' ({result.page_url})"
        )
