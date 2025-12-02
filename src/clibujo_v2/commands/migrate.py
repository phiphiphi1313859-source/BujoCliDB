"""Migration-related CLI commands for CLIBuJo v2."""

import click
from datetime import date

from ..core.db import ensure_db
from ..core.migrations import (
    migrate_to_date,
    migrate_to_month,
    migrate_to_collection,
    migrate_forward,
    get_migration_history,
    get_tasks_needing_migration,
    bulk_migrate_to_today,
)
from ..core.entries import get_entry
from ..core.collections import get_collection_by_name, get_collection
from .entries import parse_date_arg
from .display import format_entry


@click.group()
def migrate():
    """Migrate tasks between logs and collections."""
    ensure_db()


@migrate.command("forward")
@click.argument("entry_id", type=int)
def forward(entry_id: int):
    """Migrate a task to today."""
    entry = migrate_forward(entry_id)
    if entry:
        click.echo(f"Migrated to today: {format_entry(entry)}")
    else:
        original = get_entry(entry_id)
        if not original:
            raise click.ClickException(f"Entry not found: {entry_id}")
        elif original.entry_type != "task":
            raise click.ClickException("Only tasks can be migrated")
        elif original.status != "open":
            raise click.ClickException(f"Task is not open (status: {original.status})")
        else:
            raise click.ClickException("Migration failed")


@migrate.command("to-date")
@click.argument("entry_id", type=int)
@click.argument("date_arg")
def to_date(entry_id: int, date_arg: str):
    """Migrate a task to a specific date."""
    target_date = parse_date_arg(date_arg)
    entry = migrate_to_date(entry_id, target_date)

    if entry:
        click.echo(f"Migrated to {target_date}: {format_entry(entry)}")
    else:
        original = get_entry(entry_id)
        if not original:
            raise click.ClickException(f"Entry not found: {entry_id}")
        elif original.entry_type != "task":
            raise click.ClickException("Only tasks can be migrated")
        elif original.status != "open":
            raise click.ClickException(f"Task is not open (status: {original.status})")
        else:
            raise click.ClickException("Migration failed")


@migrate.command("to-month")
@click.argument("entry_id", type=int)
@click.argument("month")
def to_month(entry_id: int, month: str):
    """Schedule a task for a future month."""
    entry = migrate_to_month(entry_id, month)

    if entry:
        click.echo(f"Scheduled for {month}: {format_entry(entry)}")
    else:
        original = get_entry(entry_id)
        if not original:
            raise click.ClickException(f"Entry not found: {entry_id}")
        elif original.entry_type != "task":
            raise click.ClickException("Only tasks can be migrated")
        elif original.status != "open":
            raise click.ClickException(f"Task is not open (status: {original.status})")
        else:
            raise click.ClickException("Migration failed")


@migrate.command("to-collection")
@click.argument("entry_id", type=int)
@click.argument("collection")
def to_collection(entry_id: int, collection: str):
    """Migrate a task to a collection."""
    # Try as ID first
    try:
        coll_id = int(collection)
        coll = get_collection(coll_id)
    except ValueError:
        coll = get_collection_by_name(collection)

    if not coll:
        raise click.ClickException(f"Collection not found: {collection}")

    entry = migrate_to_collection(entry_id, coll.id)

    if entry:
        click.echo(f"Migrated to {coll.name}: {format_entry(entry)}")
    else:
        original = get_entry(entry_id)
        if not original:
            raise click.ClickException(f"Entry not found: {entry_id}")
        elif original.entry_type != "task":
            raise click.ClickException("Only tasks can be migrated")
        elif original.status != "open":
            raise click.ClickException(f"Task is not open (status: {original.status})")
        else:
            raise click.ClickException("Migration failed")


@migrate.command("review")
@click.option("--before", "-b", "before_date", help="Show tasks before this date")
def review(before_date: str):
    """Review tasks that may need migration.

    Shows open tasks from past dates that haven't been migrated forward.
    """
    if before_date:
        target = parse_date_arg(before_date)
    else:
        target = date.today().isoformat()

    tasks = get_tasks_needing_migration(target)

    if not tasks:
        click.echo("No open tasks need migration.")
        return

    click.echo(f"== Open Tasks Before {target} ==\n")

    # Group by date
    by_date = {}
    for task in tasks:
        key = task.entry_date or task.entry_month or "undated"
        if key not in by_date:
            by_date[key] = []
        by_date[key].append(task)

    for date_key in sorted(by_date.keys()):
        click.echo(f"{date_key}:")
        for task in by_date[date_key]:
            click.echo(f"  {format_entry(task)}")
        click.echo()

    click.echo(f"Total: {len(tasks)} task(s) may need migration")
    click.echo("\nUse 'bujo migrate forward <id>' to migrate individual tasks")
    click.echo("Or 'bujo migrate bulk' to migrate all to today")


@migrate.command("bulk")
@click.option("--before", "-b", "before_date", help="Migrate tasks before this date")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def bulk(before_date: str, yes: bool):
    """Migrate all old open tasks to today."""
    if before_date:
        target = parse_date_arg(before_date)
    else:
        target = date.today().isoformat()

    tasks = get_tasks_needing_migration(target)

    if not tasks:
        click.echo("No tasks to migrate.")
        return

    if not yes:
        click.confirm(f"Migrate {len(tasks)} task(s) to today?", abort=True)

    entry_ids = [t.id for t in tasks]
    new_entries = bulk_migrate_to_today(entry_ids)

    click.echo(f"Migrated {len(new_entries)} task(s) to today:")
    for entry in new_entries:
        click.echo(f"  {format_entry(entry)}")


@migrate.command("history")
@click.argument("entry_id", type=int)
def history(entry_id: int):
    """View migration history for an entry."""
    entry = get_entry(entry_id)
    if not entry:
        raise click.ClickException(f"Entry not found: {entry_id}")

    migrations = get_migration_history(entry_id)

    if not migrations:
        click.echo(f"No migration history for entry #{entry_id}")
        click.echo(f"  {format_entry(entry)}")
        return

    click.echo(f"== Migration History for #{entry_id} ==\n")
    click.echo(f"Current: {format_entry(entry)}\n")

    for m in migrations:
        from_loc = m.from_date or m.from_month or f"collection #{m.from_collection_id}" or "unknown"
        to_loc = m.to_date or m.to_month or f"collection #{m.to_collection_id}" or "unknown"
        click.echo(f"  {m.migrated_at}: {from_loc} -> {to_loc}")
