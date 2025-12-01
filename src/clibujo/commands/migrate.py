"""Migration commands for CLIBuJo"""

from datetime import date
from typing import Optional

from rich.console import Console

from ..core.config import Config
from ..core.database import Database
from ..core.indexer import Indexer
from ..core.models import TaskStatus, UndoAction
from ..core.parser import (
    update_task_status,
    add_migration_hint,
    create_migrated_entry,
)
from ..utils.files import (
    update_line,
    append_line,
    append_to_section,
    get_daily_file,
    get_monthly_file,
    get_future_file,
    get_collection_file,
    create_monthly_file,
    create_future_file,
)
from ..utils.dates import parse_month, get_month_name, get_next_month

console = Console()


def migrate_task(
    config: Config,
    db: Database,
    indexer: Indexer,
    ref: str,
    destination: Optional[str],
):
    """Migrate a task to another location"""
    # Find the entry
    entry = db.get_entry_by_ref(ref)
    if not entry:
        entry = db.get_entry_by_ref_prefix(ref)

    if not entry:
        # Try as numeric index for today
        try:
            idx = int(ref)
            today = date.today()
            entries = db.get_entries_by_date(today)
            tasks = [e for e in entries if e.entry_type == "task"]
            if 1 <= idx <= len(tasks):
                entry = tasks[idx - 1]
        except ValueError:
            pass

    if not entry:
        console.print(f"[red]Entry not found: {ref}[/red]")
        return

    if entry.entry_type != "task":
        console.print(f"[red]Entry is not a task[/red]")
        return

    if entry.status in ("complete", "migrated", "scheduled", "cancelled"):
        console.print(f"[red]Task already {entry.status}[/red]")
        return

    # Get destination if not provided
    if not destination:
        console.print()
        console.print(f"Migrating: {entry.content}")
        console.print()
        console.print("Destination:")
        console.print("  [m] Next month")
        console.print("  [f] Future log")
        console.print("  [c] Collection")
        console.print("  [Enter] Cancel")
        console.print()

        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "m":
            today = date.today()
            next_year, next_month = get_next_month(today.year, today.month)
            destination = f"monthly/{next_year}-{next_month:02d}"
        elif choice == "f":
            console.print("Which month? (1-12, YYYY-MM, or 'someday'): ", end="")
            try:
                month_input = input().strip()
            except (EOFError, KeyboardInterrupt):
                return

            if month_input.lower() == "someday":
                destination = "future/someday"
            else:
                parsed = parse_month(month_input)
                if parsed:
                    year, month = parsed
                    destination = f"future/{year}-{month:02d}"
                else:
                    console.print("[red]Invalid month[/red]")
                    return
        elif choice == "c":
            console.print("Collection name: ", end="")
            try:
                coll_name = input().strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not coll_name:
                return
            destination = f"collection/{coll_name}"
        else:
            return

    # Perform migration
    _do_migrate(config, db, indexer, entry, destination)


def schedule_task(
    config: Config,
    db: Database,
    indexer: Indexer,
    ref: str,
    month_str: str,
):
    """Schedule a task to the future log"""
    # Find the entry
    entry = db.get_entry_by_ref(ref)
    if not entry:
        entry = db.get_entry_by_ref_prefix(ref)

    if not entry:
        try:
            idx = int(ref)
            today = date.today()
            entries = db.get_entries_by_date(today)
            tasks = [e for e in entries if e.entry_type == "task"]
            if 1 <= idx <= len(tasks):
                entry = tasks[idx - 1]
        except ValueError:
            pass

    if not entry:
        console.print(f"[red]Entry not found: {ref}[/red]")
        return

    if entry.entry_type != "task":
        console.print(f"[red]Entry is not a task[/red]")
        return

    # Parse month
    if month_str.lower() == "someday":
        destination = "future/someday"
    else:
        parsed = parse_month(month_str)
        if parsed:
            year, month = parsed
            destination = f"future/{year}-{month:02d}"
        else:
            console.print(f"[red]Invalid month: {month_str}[/red]")
            return

    _do_migrate(config, db, indexer, entry, destination, scheduled=True)


def _do_migrate(
    config: Config,
    db: Database,
    indexer: Indexer,
    entry,
    destination: str,
    scheduled: bool = False,
):
    """Perform the actual migration"""
    source_file = config.data_dir / entry.source_file

    # Determine destination file and section
    if destination.startswith("monthly/"):
        # Monthly log
        parts = destination.split("/")[1]
        year, month = int(parts[:4]), int(parts[5:7])
        dest_file = create_monthly_file(config.data_dir, year, month)
        dest_hint = f"months/{year}-{month:02d}.md"
        section = "Tasks"
    elif destination.startswith("future/"):
        # Future log
        dest_file = create_future_file(config.data_dir)
        dest_hint = "future.md"
        part = destination.split("/")[1]
        if part == "someday":
            section = "Someday"
        else:
            year, month = int(part[:4]), int(part[5:7])
            section = f"{get_month_name(month)} {year}"
    elif destination.startswith("collection/"):
        # Collection
        coll_name = destination.split("/", 1)[1]
        dest_file = get_collection_file(config.data_dir, coll_name)
        if not dest_file.exists():
            console.print(f"[red]Collection not found: {coll_name}[/red]")
            return
        dest_hint = f"collections/{coll_name}.md"
        section = "Tasks"
    else:
        console.print(f"[red]Invalid destination: {destination}[/red]")
        return

    # Update source file: mark as migrated/scheduled
    new_status = TaskStatus.SCHEDULED if scheduled else TaskStatus.MIGRATED
    updated_line = update_task_status(entry.raw_line, new_status)
    updated_line = add_migration_hint(updated_line, dest_hint)

    old_line = update_line(source_file, entry.line_number, updated_line)

    # Record undo
    if old_line:
        db.add_undo_action(UndoAction(
            action_type="edit",
            file_path=str(source_file),
            line_number=entry.line_number,
            old_content=old_line,
            new_content=updated_line,
        ))

    # Add to destination
    source_hint = entry.source_file
    new_entry = create_migrated_entry(entry.content, source_hint, None)
    append_to_section(dest_file, section, new_entry)

    # Reindex both files
    indexer.reindex_file(source_file)
    indexer.reindex_file(dest_file)

    action = "Scheduled" if scheduled else "Migrated"
    console.print(f"[green]{action}:[/green] {entry.content}")
    console.print(f"  → {dest_hint}")
