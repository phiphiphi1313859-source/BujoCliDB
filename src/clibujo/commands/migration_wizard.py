"""Monthly migration wizard for CLIBuJo"""

from datetime import date

from rich.console import Console

from ..core.config import Config
from ..core.database import Database
from ..core.indexer import Indexer
from ..core.models import TaskStatus, UndoAction
from ..core.parser import update_task_status, add_migration_hint, create_migrated_entry
from ..utils.files import (
    update_line,
    append_to_section,
    create_monthly_file,
    create_future_file,
    get_collection_file,
)
from ..utils.dates import get_month_name, get_prev_month, days_between

console = Console()


def migration_wizard(config: Config, db: Database, indexer: Indexer):
    """Run the monthly migration wizard"""
    today = date.today()
    current_year, current_month = today.year, today.month
    prev_year, prev_month = get_prev_month(current_year, current_month)

    prev_month_name = get_month_name(prev_month)
    current_month_name = get_month_name(current_month)

    console.print()
    console.print(f"[bold]Monthly Migration: {prev_month_name} {prev_year} → {current_month_name} {current_year}[/bold]")
    console.print()

    # Get all open tasks from the previous month and earlier
    open_tasks = db.get_open_tasks(to_date=date(current_year, current_month, 1))

    if not open_tasks:
        console.print("[green]No incomplete tasks to migrate![/green]")
        return

    console.print(f"Reviewing {len(open_tasks)} incomplete task(s)...")
    console.print()

    stats = {
        "kept": 0,
        "future": 0,
        "collection": 0,
        "dropped": 0,
        "skipped": 0,
    }

    for i, task in enumerate(open_tasks, 1):
        console.print(f"[bold][{i}/{len(open_tasks)}][/bold] {task.content}")
        console.print(f"       Source: {task.source_file}")

        # Show age
        if task.entry_date:
            age = days_between(task.entry_date, today)
            if age > 14:
                console.print(f"       [yellow]Age: {age} days[/yellow]")
            else:
                console.print(f"       Age: {age} days")

        console.print()
        console.print("       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: ", end="")

        try:
            choice = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Migration cancelled[/yellow]")
            return

        if choice == "k":
            # Keep - migrate to current month
            _migrate_to_month(config, db, indexer, task, current_year, current_month)
            stats["kept"] += 1
            console.print("       [green]→ Migrated to current month[/green]")

        elif choice == "d":
            # Drop - mark as cancelled
            _cancel_task(config, db, indexer, task)
            stats["dropped"] += 1
            console.print("       [dim]→ Dropped[/dim]")

        elif choice == "f":
            # Future log
            console.print("       Which month? (1-12, or 'someday'): ", end="")
            try:
                month_input = input().strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Skipped[/yellow]")
                stats["skipped"] += 1
                continue

            if month_input.lower() == "someday":
                _migrate_to_future(config, db, indexer, task, None)
            else:
                try:
                    month_num = int(month_input)
                    if 1 <= month_num <= 12:
                        # Determine year
                        target_year = current_year if month_num >= current_month else current_year + 1
                        _migrate_to_future(config, db, indexer, task, (target_year, month_num))
                    else:
                        console.print("       [red]Invalid month, skipping[/red]")
                        stats["skipped"] += 1
                        continue
                except ValueError:
                    console.print("       [red]Invalid month, skipping[/red]")
                    stats["skipped"] += 1
                    continue

            stats["future"] += 1
            console.print("       [green]→ Scheduled to future log[/green]")

        elif choice == "c":
            # Collection
            console.print("       Collection name: ", end="")
            try:
                coll_name = input().strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Skipped[/yellow]")
                stats["skipped"] += 1
                continue

            if not coll_name:
                stats["skipped"] += 1
                continue

            coll_file = get_collection_file(config.data_dir, coll_name)
            if not coll_file.exists():
                console.print(f"       [red]Collection '{coll_name}' not found[/red]")
                stats["skipped"] += 1
                continue

            _migrate_to_collection(config, db, indexer, task, coll_name)
            stats["collection"] += 1
            console.print(f"       [green]→ Moved to {coll_name}[/green]")

        elif choice == "s":
            stats["skipped"] += 1
            console.print("       [dim]→ Skipped[/dim]")

        else:
            stats["skipped"] += 1
            console.print("       [dim]→ Skipped[/dim]")

        console.print()

    # Summary
    console.print()
    console.print("[bold]Migration complete![/bold]")
    console.print(f"  Kept:       {stats['kept']}")
    console.print(f"  Future:     {stats['future']}")
    console.print(f"  Collection: {stats['collection']}")
    console.print(f"  Dropped:    {stats['dropped']}")
    if stats["skipped"] > 0:
        console.print(f"  Skipped:    {stats['skipped']}")
    console.print()


def _migrate_to_month(
    config: Config,
    db: Database,
    indexer: Indexer,
    task,
    year: int,
    month: int,
):
    """Migrate task to a monthly log"""
    source_file = config.data_dir / task.source_file
    dest_file = create_monthly_file(config.data_dir, year, month)
    dest_hint = f"months/{year}-{month:02d}.md"

    # Update source
    updated_line = update_task_status(task.raw_line, TaskStatus.MIGRATED)
    updated_line = add_migration_hint(updated_line, dest_hint)
    old_line = update_line(source_file, task.line_number, updated_line)

    if old_line:
        db.add_undo_action(UndoAction(
            action_type="edit",
            file_path=str(source_file),
            line_number=task.line_number,
            old_content=old_line,
            new_content=updated_line,
        ))

    # Add to destination
    new_entry = create_migrated_entry(task.content, task.source_file, None)
    append_to_section(dest_file, "Tasks", new_entry)

    indexer.reindex_file(source_file)
    indexer.reindex_file(dest_file)


def _migrate_to_future(
    config: Config,
    db: Database,
    indexer: Indexer,
    task,
    target_month: tuple[int, int] | None,
):
    """Migrate task to future log"""
    source_file = config.data_dir / task.source_file
    dest_file = create_future_file(config.data_dir)
    dest_hint = "future.md"

    # Determine section
    if target_month:
        year, month = target_month
        section = f"{get_month_name(month)} {year}"
    else:
        section = "Someday"

    # Update source
    updated_line = update_task_status(task.raw_line, TaskStatus.SCHEDULED)
    updated_line = add_migration_hint(updated_line, dest_hint)
    old_line = update_line(source_file, task.line_number, updated_line)

    if old_line:
        db.add_undo_action(UndoAction(
            action_type="edit",
            file_path=str(source_file),
            line_number=task.line_number,
            old_content=old_line,
            new_content=updated_line,
        ))

    # Add to destination
    new_entry = create_migrated_entry(task.content, task.source_file, None)
    append_to_section(dest_file, section, new_entry)

    indexer.reindex_file(source_file)
    indexer.reindex_file(dest_file)


def _migrate_to_collection(
    config: Config,
    db: Database,
    indexer: Indexer,
    task,
    collection_name: str,
):
    """Migrate task to a collection"""
    source_file = config.data_dir / task.source_file
    dest_file = get_collection_file(config.data_dir, collection_name)
    dest_hint = f"collections/{collection_name}.md"

    # Update source
    updated_line = update_task_status(task.raw_line, TaskStatus.MIGRATED)
    updated_line = add_migration_hint(updated_line, dest_hint)
    old_line = update_line(source_file, task.line_number, updated_line)

    if old_line:
        db.add_undo_action(UndoAction(
            action_type="edit",
            file_path=str(source_file),
            line_number=task.line_number,
            old_content=old_line,
            new_content=updated_line,
        ))

    # Add to destination
    new_entry = create_migrated_entry(task.content, task.source_file, None)
    append_to_section(dest_file, "Tasks", new_entry)

    indexer.reindex_file(source_file)
    indexer.reindex_file(dest_file)


def _cancel_task(
    config: Config,
    db: Database,
    indexer: Indexer,
    task,
):
    """Cancel a task"""
    source_file = config.data_dir / task.source_file

    updated_line = update_task_status(task.raw_line, TaskStatus.CANCELLED)
    old_line = update_line(source_file, task.line_number, updated_line)

    if old_line:
        db.add_undo_action(UndoAction(
            action_type="edit",
            file_path=str(source_file),
            line_number=task.line_number,
            old_content=old_line,
            new_content=updated_line,
        ))

    indexer.reindex_file(source_file)
