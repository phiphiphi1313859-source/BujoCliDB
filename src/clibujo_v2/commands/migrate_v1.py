"""CLI command for migrating from v1 markdown format."""

import click
from pathlib import Path

from ..core.db import ensure_db
from ..utils.migrate_v1 import migrate_from_path, find_v1_data_dir


@click.command("import-v1")
@click.option("--path", "-p", type=click.Path(exists=True), help="Path to v1 data directory")
@click.option("--dry-run", "-n", is_flag=True, help="Preview what would be imported")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def import_v1(path, dry_run, yes):
    """Import data from CLIBuJo v1 (markdown format).

    This will import daily logs, monthly logs, collections, and habits
    from the v1 markdown file structure into the v2 SQLite database.

    Use --dry-run to preview what would be imported without making changes.
    """
    ensure_db()

    # Find v1 directory
    if path:
        v1_dir = Path(path)
    else:
        v1_dir = find_v1_data_dir()
        if not v1_dir:
            raise click.ClickException(
                "Could not find v1 data directory. "
                "Please specify --path to your v1 data location."
            )

    click.echo(f"V1 data directory: {v1_dir}")

    # Do dry run first
    if dry_run or not yes:
        click.echo("\nScanning v1 data...")
        stats = migrate_from_path(str(v1_dir), dry_run=True)

        click.echo(f"\nFound:")
        click.echo(f"  Daily logs: {stats['daily_logs']}")
        click.echo(f"  Entries: {stats['entries']}")
        click.echo(f"  Collections: {stats['collections']}")
        click.echo(f"  Collection entries: {stats['collection_entries']}")
        click.echo(f"  Habits: {stats['habits']}")

        if stats["errors"]:
            click.echo(f"\nWarnings/Errors ({len(stats['errors'])}):")
            for err in stats["errors"][:10]:
                click.echo(f"  - {err}")
            if len(stats["errors"]) > 10:
                click.echo(f"  ... and {len(stats['errors']) - 10} more")

        if dry_run:
            click.echo("\nDry run complete. No changes made.")
            return

        if not yes:
            click.confirm("\nProceed with import?", abort=True)

    # Do the actual import
    click.echo("\nImporting data...")
    stats = migrate_from_path(str(v1_dir), dry_run=False)

    click.echo(f"\nImported:")
    click.echo(f"  Daily logs: {stats['daily_logs']}")
    click.echo(f"  Entries: {stats['entries']}")
    click.echo(f"  Collections: {stats['collections']}")
    click.echo(f"  Collection entries: {stats['collection_entries']}")
    click.echo(f"  Habits: {stats['habits']}")

    if stats["errors"]:
        click.echo(f"\nWarnings/Errors ({len(stats['errors'])}):")
        for err in stats["errors"][:10]:
            click.echo(f"  - {err}")

    click.echo("\nImport complete!")
