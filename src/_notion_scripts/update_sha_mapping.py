"""Update SHA mapping for Notion file uploads.

This CLI tool helps manage the SHA mapping file that maps file hashes to
Notion URLs to avoid re-uploading files that have already been uploaded.
"""

import hashlib
import json
import sys
from http import HTTPStatus
from pathlib import Path

import click
import requests
from beartype import beartype


@beartype
def _calculate_file_sha(*, file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.
    """
    sha256_hash = hashlib.sha256()
    with file_path.open(mode="rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


@beartype
def _load_sha_mapping(*, mapping_file: Path) -> dict[str, str]:
    """
    Load existing SHA mapping from file.
    """
    if not mapping_file.exists():
        return {}
    try:
        content = mapping_file.read_text(encoding="utf-8")
        return dict(json.loads(s=content))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        click.echo(message=f"Error reading SHA mapping file: {e}", err=True)
        sys.exit(1)


@beartype
def _save_sha_mapping(*, mapping_file: Path, mapping: dict[str, str]) -> None:
    """
    Save SHA mapping to file.
    """
    mapping_file.parent.mkdir(parents=True, exist_ok=True)
    mapping_file.write_text(
        data=json.dumps(obj=mapping, indent=2, sort_keys=True),
        encoding="utf-8",
    )


@beartype
def _validate_notion_url(*, url: str) -> bool:
    """
    Validate that a Notion URL is accessible.
    """
    try:
        response = requests.head(url=url, timeout=10)
        return response.status_code == HTTPStatus.OK
    except requests.RequestException:
        return False


@click.group()
def cli() -> None:
    """
    Update SHA mapping for Notion file uploads.
    """


@cli.command()
@click.option(
    "--mapping-file",
    help="Path to the SHA mapping JSON file",
    required=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--file",
    help="Local file to add to mapping",
    required=True,
    type=click.Path(
        exists=True,
        path_type=Path,
        file_okay=True,
        dir_okay=False,
    ),
)
@click.option(
    "--notion-url",
    help="Notion URL for the uploaded file",
    required=True,
)
@click.option(
    "--validate-url/--no-validate-url",
    help="Validate that the Notion URL is accessible",
    default=True,
)
@beartype
def add(
    *,
    mapping_file: Path,
    file: Path,
    notion_url: str,
    validate_url: bool,
) -> None:
    """
    Add a file SHA to Notion URL mapping.
    """
    # Load existing mapping
    sha_mapping = _load_sha_mapping(mapping_file=mapping_file)

    # Calculate file SHA
    file_sha = _calculate_file_sha(file_path=file)
    click.echo(message=f"File SHA: {file_sha}")

    # Validate Notion URL if requested
    if validate_url and not _validate_notion_url(url=notion_url):
        click.echo(
            message=f"Warning: Notion URL is not accessible: {notion_url}",
            err=True,
        )
        if not click.confirm(text="Continue anyway?"):
            sys.exit(1)

    # Add to mapping
    sha_mapping[file_sha] = notion_url

    # Save mapping
    _save_sha_mapping(mapping_file=mapping_file, mapping=sha_mapping)
    click.echo(message=f"Added mapping: {file_sha} -> {notion_url}")


@cli.command()
@click.option(
    "--mapping-file",
    help="Path to the SHA mapping JSON file",
    required=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--file",
    help="Local file to remove from mapping",
    required=True,
    type=click.Path(
        exists=True,
        path_type=Path,
        file_okay=True,
        dir_okay=False,
    ),
)
@beartype
def remove(
    *,
    mapping_file: Path,
    file: Path,
) -> None:
    """
    Remove a file SHA from the mapping.
    """
    # Load existing mapping
    sha_mapping = _load_sha_mapping(mapping_file=mapping_file)

    # Calculate file SHA
    file_sha = _calculate_file_sha(file_path=file)

    if file_sha in sha_mapping:
        notion_url = sha_mapping.pop(file_sha)
        _save_sha_mapping(mapping_file=mapping_file, mapping=sha_mapping)
        click.echo(message=f"Removed mapping: {file_sha} -> {notion_url}")
    else:
        click.echo(message=f"No mapping found for file SHA: {file_sha}")


@cli.command()
@click.option(
    "--mapping-file",
    help="Path to the SHA mapping JSON file",
    required=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--validate-all",
    help="Validate all Notion URLs in the mapping",
    is_flag=True,
    default=False,
)
@beartype
def list_mappings(
    *,
    mapping_file: Path,
    validate_all: bool,
) -> None:
    """
    List all mappings in the SHA mapping file.
    """
    # Load existing mapping
    sha_mapping = _load_sha_mapping(mapping_file=mapping_file)

    if not sha_mapping:
        click.echo(message="No mappings found.")
        return

    click.echo(message=f"Found {len(sha_mapping)} mappings:")
    for sha, notion_url in sha_mapping.items():
        status = (
            " ✓"
            if validate_all and _validate_notion_url(url=notion_url)
            else " ✗"
            if validate_all
            else ""
        )
        click.echo(message=f"  {sha[:16]}... -> {notion_url}{status}")


@cli.command()
@click.option(
    "--mapping-file",
    help="Path to the SHA mapping JSON file",
    required=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--remove-invalid",
    help="Remove mappings with invalid URLs",
    is_flag=True,
    default=False,
)
@beartype
def validate(
    *,
    mapping_file: Path,
    remove_invalid: bool,
) -> None:
    """
    Validate all Notion URLs in the mapping.
    """
    # Load existing mapping
    sha_mapping = _load_sha_mapping(mapping_file=mapping_file)

    if not sha_mapping:
        click.echo(message="No mappings to validate.")
        return

    invalid_mappings: list[tuple[str, str]] = []
    valid_count = 0

    click.echo(message="Validating Notion URLs...")
    for sha, notion_url in sha_mapping.items():
        if _validate_notion_url(url=notion_url):
            valid_count += 1
            click.echo(message=f"  ✓ {sha[:16]}... -> {notion_url}")
        else:
            invalid_mappings.append((sha, notion_url))
            click.echo(message=f"  ✗ {sha[:16]}... -> {notion_url}")

    click.echo(
        message=f"\nValidation complete: {valid_count} valid, "
        f"{len(invalid_mappings)} invalid"
    )

    if invalid_mappings and remove_invalid:
        if click.confirm(
            text=f"Remove {len(invalid_mappings)} invalid mappings?"
        ):
            for sha, _ in invalid_mappings:
                sha_mapping.pop(sha)
            _save_sha_mapping(mapping_file=mapping_file, mapping=sha_mapping)
            click.echo(message="Invalid mappings removed.")


@cli.command()
@click.option(
    "--mapping-file",
    help="Path to the SHA mapping JSON file",
    required=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--file",
    help="Local file to check",
    required=True,
    type=click.Path(
        exists=True,
        path_type=Path,
        file_okay=True,
        dir_okay=False,
    ),
)
@beartype
def check(
    *,
    mapping_file: Path,
    file: Path,
) -> None:
    """
    Check if a file has a mapping in the SHA mapping file.
    """
    # Load existing mapping
    sha_mapping = _load_sha_mapping(mapping_file=mapping_file)

    # Calculate file SHA
    file_sha = _calculate_file_sha(file_path=file)

    if file_sha in sha_mapping:
        notion_url = sha_mapping[file_sha]
        is_valid = _validate_notion_url(url=notion_url)
        status = "valid" if is_valid else "invalid"
        click.echo(message=f"File has mapping: {notion_url} ({status})")
    else:
        click.echo(message="File has no mapping.")


if __name__ == "__main__":
    cli()
