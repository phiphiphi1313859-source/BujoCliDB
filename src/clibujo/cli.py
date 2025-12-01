"""Main CLI entry point for CLIBuJo"""

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .core.config import Config, load_config, save_config, get_default_config_yaml
from .core.database import Database
from .core.indexer import Indexer, init_bujo, startup_reindex
from .core.models import EntryType, TaskStatus, Signifier, UndoAction
from .core.parser import (
    parse_entry,
    entry_to_markdown,
    update_task_status,
    add_migration_hint,
    create_migrated_entry,
    generate_entry_ref,
)
from .utils.files import (
    ensure_data_dirs,
    get_daily_file,
    get_monthly_file,
    get_future_file,
    get_collection_file,
    get_index_file,
    read_file_lines,
    append_line,
    update_line,
    create_daily_file,
    create_monthly_file,
    create_future_file,
    create_collection_file,
    append_to_section,
    walk_markdown_files,
)
from .utils.dates import (
    parse_date,
    format_date,
    format_short_date,
    get_month_name,
    get_week_dates,
    parse_month,
    get_next_month,
)
from .utils.display import get_terminal_width, truncate, is_narrow_terminal

app = typer.Typer(
    name="bujo",
    help="CLI Bullet Journal - A command-line bullet journal",
    no_args_is_help=False,
)
console = Console()

# Global state
_config: Optional[Config] = None
_db: Optional[Database] = None
_indexer: Optional[Indexer] = None


def get_app_state() -> tuple[Config, Database, Indexer]:
    """Get or initialize application state"""
    global _config, _db, _indexer

    if _config is None:
        _config = load_config()
        ensure_data_dirs(_config.data_dir)

    if _db is None or _indexer is None:
        _db, _indexer = init_bujo(_config)

    return _config, _db, _indexer


def do_startup() -> tuple[Config, Database, Indexer]:
    """Perform startup tasks including sync and reindex"""
    config, db, indexer = get_app_state()

    # Auto-pull if configured
    if config.sync.enabled and config.sync.auto_pull:
        try:
            from .commands.sync import git_pull
            git_pull(config)
        except Exception:
            pass  # Ignore sync errors on startup

    # Reindex
    changed = startup_reindex(config, db, indexer)
    if changed > 0:
        console.print(f"[dim]Reindexed {changed} file(s)[/dim]")

    return config, db, indexer


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """CLIBuJo - CLI Bullet Journal

    Run without arguments to show today's log in interactive mode.
    """
    if ctx.invoked_subcommand is None:
        # No subcommand - show interactive mode
        from .commands.interactive import interactive_mode
        config, db, indexer = do_startup()
        interactive_mode(config, db, indexer)


@app.command()
def add(
    entry: Optional[str] = typer.Argument(None, help="Entry text (auto-detects type from prefix)"),
    task: Optional[str] = typer.Option(None, "-t", "--task", help="Add as task"),
    event: Optional[str] = typer.Option(None, "-e", "--event", help="Add as event"),
    note: Optional[str] = typer.Option(None, "-n", "--note", help="Add as note"),
    priority: bool = typer.Option(False, "-p", "--priority", help="Mark as priority"),
    to_collection: Optional[str] = typer.Option(None, "-c", "--collection", help="Add to collection"),
    to_future: Optional[str] = typer.Option(None, "-f", "--future", help="Add to future log month"),
):
    """Add an entry to today's log (or specified destination)"""
    config, db, indexer = get_app_state()

    # Determine entry text and type
    if task:
        text = task
        entry_type = EntryType.TASK
    elif event:
        text = event
        entry_type = EntryType.EVENT
    elif note:
        text = note
        entry_type = EntryType.NOTE
    elif entry:
        # Try to parse from prefix
        parsed = parse_entry(entry, signifiers=config.signifiers)
        if parsed:
            text = parsed.content
            entry_type = parsed.entry_type
            if parsed.signifier == Signifier.PRIORITY:
                priority = True
        else:
            # Default to task
            text = entry
            entry_type = EntryType.TASK
    else:
        console.print("[red]No entry text provided[/red]")
        raise typer.Exit(1)

    # Build the entry line
    parts = []
    if priority:
        parts.append("*")

    if entry_type == EntryType.TASK:
        parts.append("[ ]")
    elif entry_type == EntryType.EVENT:
        parts.append("○")
    elif entry_type == EntryType.NOTE:
        parts.append("-")

    parts.append(text)
    line = " ".join(parts)

    # Determine destination
    if to_collection:
        file_path = get_collection_file(config.data_dir, to_collection)
        if not file_path.exists():
            console.print(f"[red]Collection '{to_collection}' not found[/red]")
            raise typer.Exit(1)
        line_num = append_to_section(file_path, "Tasks", line)
    elif to_future:
        parsed_month = parse_month(to_future)
        if not parsed_month:
            console.print(f"[red]Invalid month: {to_future}[/red]")
            raise typer.Exit(1)
        file_path = get_future_file(config.data_dir)
        create_future_file(config.data_dir)
        # Find or create month section
        year, month = parsed_month
        section = f"{get_month_name(month)} {year}"
        line_num = append_to_section(file_path, section, line)
    else:
        # Add to today's daily log
        today = date.today()
        file_path = create_daily_file(config.data_dir, today)
        line_num = append_line(file_path, line)

    # Reindex the file
    indexer.reindex_file(file_path)

    # Show confirmation
    console.print(f"[green]Added:[/green] {line}")


@app.command()
def day(
    date_str: Optional[str] = typer.Argument(None, help="Date to view (default: today)"),
    edit: bool = typer.Option(False, "-e", "--edit", help="Open in editor"),
):
    """View a daily log"""
    config, db, indexer = get_app_state()

    if date_str:
        target_date = parse_date(date_str)
        if not target_date:
            console.print(f"[red]Invalid date: {date_str}[/red]")
            raise typer.Exit(1)
    else:
        target_date = date.today()

    file_path = get_daily_file(config.data_dir, target_date)

    if edit:
        from .commands.editor import open_in_editor
        open_in_editor(config, file_path)
        indexer.reindex_file(file_path)
        return

    # Display the day
    _display_daily_log(config, db, target_date, file_path)


def _display_daily_log(config: Config, db: Database, target_date: date, file_path: Path):
    """Display a daily log"""
    width = get_terminal_width()
    narrow = is_narrow_terminal(config.narrow_threshold)

    # Header
    date_str = format_date(target_date, config.date_format)
    if narrow:
        console.print(f"[bold]{format_short_date(target_date)}[/bold]")
    else:
        console.print()
        console.print(f"[bold]CLIBuJo[/bold]" + " " * (width - 7 - len(date_str)) + date_str)
        console.print()
        console.print("═" * width)

    if not file_path.exists():
        console.print("\n[dim](empty day — start logging!)[/dim]\n")
        return

    # Read and display entries
    lines = read_file_lines(file_path)
    entries = db.get_entries_by_file(str(file_path.relative_to(config.data_dir)))

    task_index = 1
    for entry in entries:
        line = _format_entry_line(entry, task_index, config.show_entry_refs, width if narrow else None)
        console.print(line)
        if entry.entry_type == "task":
            task_index += 1

    console.print()


def _format_entry_line(
    entry,
    task_index: int,
    show_refs: bool,
    max_width: Optional[int] = None,
) -> str:
    """Format an entry for display"""
    parts = []

    # Signifier
    if entry.signifier:
        sig_map = {"priority": "*", "inspiration": "!", "explore": "?", "waiting": "@", "delegated": "#"}
        parts.append(sig_map.get(entry.signifier, " "))
    else:
        parts.append(" ")

    # Entry type marker
    if entry.entry_type == "task":
        status_map = {"open": "[ ]", "complete": "[x]", "migrated": "[>]", "scheduled": "[<]", "cancelled": "[~]"}
        parts.append(status_map.get(entry.status, "[ ]"))
    elif entry.entry_type == "event":
        parts.append("○  ")
    elif entry.entry_type == "note":
        parts.append("-  ")

    # Index or ref
    if entry.entry_type == "task":
        if show_refs:
            parts.append(f"[{entry.entry_ref}]")
        else:
            parts.append(f"[{task_index}]")
    else:
        parts.append("   ")

    # Content
    parts.append(entry.content)

    line = " ".join(parts)

    if max_width:
        line = truncate(line, max_width)

    return line


@app.command()
def week(
    date_str: Optional[str] = typer.Argument(None, help="Any date in the week (default: this week)"),
):
    """View the current week"""
    config, db, indexer = get_app_state()

    if date_str:
        target_date = parse_date(date_str)
        if not target_date:
            console.print(f"[red]Invalid date: {date_str}[/red]")
            raise typer.Exit(1)
    else:
        target_date = date.today()

    week_dates = get_week_dates(target_date, config.week_start)

    console.print()
    console.print(f"[bold]Week of {format_date(week_dates[0])}[/bold]")
    console.print()

    for day_date in week_dates:
        is_today = day_date == date.today()
        entries = db.get_entries_by_date(day_date)
        task_count = sum(1 for e in entries if e.entry_type == "task")
        done_count = sum(1 for e in entries if e.entry_type == "task" and e.status == "complete")

        day_label = format_short_date(day_date)
        if is_today:
            day_label = f"[bold cyan]{day_label}[/bold cyan]"

        if entries:
            console.print(f"{day_label}: {done_count}/{task_count} tasks, {len(entries)} entries")
        else:
            console.print(f"{day_label}: [dim]—[/dim]")

    console.print()


@app.command()
def month(
    month_str: Optional[str] = typer.Argument(None, help="Month to view (default: current)"),
    edit: bool = typer.Option(False, "-e", "--edit", help="Open in editor"),
):
    """View a monthly log"""
    config, db, indexer = get_app_state()

    if month_str:
        parsed = parse_month(month_str)
        if not parsed:
            console.print(f"[red]Invalid month: {month_str}[/red]")
            raise typer.Exit(1)
        year, month_num = parsed
    else:
        today = date.today()
        year, month_num = today.year, today.month

    file_path = get_monthly_file(config.data_dir, year, month_num)

    if edit:
        from .commands.editor import open_in_editor
        create_monthly_file(config.data_dir, year, month_num)
        open_in_editor(config, file_path)
        indexer.reindex_file(file_path)
        return

    if not file_path.exists():
        create_monthly_file(config.data_dir, year, month_num)

    # Display
    console.print()
    console.print(f"[bold]{get_month_name(month_num)} {year}[/bold]")
    console.print()

    lines = read_file_lines(file_path)
    for line in lines:
        console.print(line.rstrip())


@app.command()
def future(
    edit: bool = typer.Option(False, "-e", "--edit", help="Open in editor"),
):
    """View the future log"""
    config, db, indexer = get_app_state()

    file_path = get_future_file(config.data_dir)

    if edit:
        from .commands.editor import open_in_editor
        create_future_file(config.data_dir)
        open_in_editor(config, file_path)
        indexer.reindex_file(file_path)
        return

    if not file_path.exists():
        create_future_file(config.data_dir)

    console.print()
    lines = read_file_lines(file_path)
    for line in lines:
        console.print(line.rstrip())


@app.command()
def index():
    """View the master index"""
    config, db, indexer = get_app_state()

    # Generate index
    from .commands.index_cmd import generate_index
    generate_index(config, db)


@app.command()
def complete(
    ref: str = typer.Argument(..., help="Entry reference or index"),
):
    """Mark a task as complete"""
    config, db, indexer = get_app_state()
    _update_task_status(config, db, indexer, ref, TaskStatus.COMPLETE)


@app.command()
def cancel(
    ref: str = typer.Argument(..., help="Entry reference or index"),
):
    """Mark a task as cancelled"""
    config, db, indexer = get_app_state()
    _update_task_status(config, db, indexer, ref, TaskStatus.CANCELLED)


def _update_task_status(
    config: Config,
    db: Database,
    indexer: Indexer,
    ref: str,
    new_status: TaskStatus,
):
    """Update a task's status"""
    # Try to find by ref or index
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
        raise typer.Exit(1)

    if entry.entry_type != "task":
        console.print(f"[red]Entry is not a task[/red]")
        raise typer.Exit(1)

    # Update the file
    file_path = config.data_dir / entry.source_file
    old_line = update_line(
        file_path,
        entry.line_number,
        update_task_status(entry.raw_line, new_status),
    )

    # Record undo action
    if old_line:
        db.add_undo_action(UndoAction(
            action_type="edit",
            file_path=str(file_path),
            line_number=entry.line_number,
            old_content=old_line,
            new_content=update_task_status(entry.raw_line, new_status),
        ))

    # Update database
    completed_at = datetime.now() if new_status == TaskStatus.COMPLETE else None
    db.update_entry_status(entry.entry_ref, new_status.value, completed_at)

    # Reindex
    indexer.reindex_file(file_path)

    status_str = new_status.value.capitalize()
    console.print(f"[green]{status_str}:[/green] {entry.content}")


@app.command()
def migrate(
    ref: str = typer.Argument(..., help="Entry reference or index"),
    destination: Optional[str] = typer.Argument(None, help="Destination (month, collection, or 'future')"),
):
    """Migrate a task to another location"""
    config, db, indexer = get_app_state()
    from .commands.migrate import migrate_task
    migrate_task(config, db, indexer, ref, destination)


@app.command()
def schedule(
    ref: str = typer.Argument(..., help="Entry reference or index"),
    month_str: str = typer.Argument(..., help="Month to schedule to"),
):
    """Schedule a task to the future log"""
    config, db, indexer = get_app_state()
    from .commands.migrate import schedule_task
    schedule_task(config, db, indexer, ref, month_str)


@app.command()
def history(
    ref: str = typer.Argument(..., help="Entry reference"),
):
    """Show migration history for an entry"""
    config, db, indexer = get_app_state()

    entry = db.get_entry_by_ref(ref)
    if not entry:
        entry = db.get_entry_by_ref_prefix(ref)

    if not entry:
        console.print(f"[red]Entry not found: {ref}[/red]")
        raise typer.Exit(1)

    console.print()
    console.print(f"[bold]History for:[/bold] {entry.content}")
    console.print()

    # Show current location
    console.print(f"  Current: {entry.source_file}:{entry.line_number}")

    if entry.migrated_from:
        console.print(f"  From: {entry.migrated_from}")
    if entry.migrated_to:
        console.print(f"  To: {entry.migrated_to}")

    console.print()


@app.command()
def migration():
    """Start the monthly migration wizard"""
    config, db, indexer = get_app_state()
    from .commands.migration_wizard import migration_wizard
    migration_wizard(config, db, indexer)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, "-l", "--limit", help="Maximum results"),
):
    """Full-text search across all entries"""
    config, db, indexer = get_app_state()

    results = db.search(query, limit)

    if not results:
        console.print(f"[dim]No results for '{query}'[/dim]")
        return

    console.print()
    console.print(f"[bold]Found {len(results)} result(s):[/bold]")
    console.print()

    for i, (entry, snippet) in enumerate(results, 1):
        # Format source
        source = entry.source_file
        if source.startswith("daily/"):
            source = source[6:-3]  # Remove daily/ and .md
        elif source.startswith("collections/"):
            source = source[12:-3]

        # Format entry
        status = ""
        if entry.entry_type == "task":
            status_map = {"open": "[ ]", "complete": "[x]", "migrated": "[>]", "scheduled": "[<]", "cancelled": "[~]"}
            status = status_map.get(entry.status, "[ ]")
        elif entry.entry_type == "event":
            status = "○"
        elif entry.entry_type == "note":
            status = "-"

        console.print(f"[dim][{i}][/dim] {source}: {status} {entry.content}")

    console.print()


@app.command()
def tasks(
    status: Optional[str] = typer.Option(None, "-s", "--status", help="Filter by status (open/complete/migrated/cancelled)"),
    collection: Optional[str] = typer.Option(None, "-c", "--collection", help="Filter by collection"),
    from_date: Optional[str] = typer.Option(None, "--from", help="From date"),
    to_date: Optional[str] = typer.Option(None, "--to", help="To date"),
    priority: bool = typer.Option(False, "-p", "--priority", help="Show only priority tasks"),
):
    """List tasks with filters"""
    config, db, indexer = get_app_state()

    # Parse dates
    from_d = parse_date(from_date) if from_date else None
    to_d = parse_date(to_date) if to_date else None

    # Query
    results = db.get_tasks(
        status=status,
        from_date=from_d,
        to_date=to_d,
        collection=collection,
        signifier="priority" if priority else None,
    )

    if not results:
        console.print("[dim]No tasks found[/dim]")
        return

    console.print()
    console.print(f"[bold]Found {len(results)} task(s):[/bold]")
    console.print()

    for entry in results:
        status_map = {"open": "[ ]", "complete": "[x]", "migrated": "[>]", "scheduled": "[<]", "cancelled": "[~]"}
        status_str = status_map.get(entry.status, "[ ]")

        sig = ""
        if entry.signifier == "priority":
            sig = "* "

        date_str = ""
        if entry.entry_date:
            date_str = f"[dim]{format_short_date(entry.entry_date)}[/dim] "

        console.print(f"  {date_str}{sig}{status_str} {entry.content}")

    console.print()


@app.command()
def stats(
    year: Optional[int] = typer.Option(None, "-y", "--year", help="Filter by year"),
    month_num: Optional[int] = typer.Option(None, "-m", "--month", help="Filter by month"),
):
    """Show task statistics"""
    config, db, indexer = get_app_state()
    from .commands.stats import show_stats
    show_stats(config, db, year, month_num)


@app.command()
def collection(
    name: Optional[str] = typer.Argument(None, help="Collection name"),
    new: bool = typer.Option(False, "--new", help="Create new collection"),
    collection_type: str = typer.Option("project", "-t", "--type", help="Collection type (project/tracker/list)"),
    edit: bool = typer.Option(False, "-e", "--edit", help="Open in editor"),
):
    """View or create a collection"""
    config, db, indexer = get_app_state()

    if not name:
        # List collections
        from .commands.collections import list_collections
        list_collections(config, db)
        return

    if new:
        # Create new collection
        file_path = create_collection_file(config.data_dir, name, collection_type)
        console.print(f"[green]Created collection:[/green] {name} ({collection_type})")
        indexer.reindex_file(file_path)

        if edit:
            from .commands.editor import open_in_editor
            open_in_editor(config, file_path)
            indexer.reindex_file(file_path)
        return

    # View existing collection
    file_path = get_collection_file(config.data_dir, name)
    if not file_path.exists():
        console.print(f"[red]Collection not found: {name}[/red]")
        console.print("[dim]Use --new to create it[/dim]")
        raise typer.Exit(1)

    if edit:
        from .commands.editor import open_in_editor
        open_in_editor(config, file_path)
        indexer.reindex_file(file_path)
        return

    # Display
    console.print()
    lines = read_file_lines(file_path)
    for line in lines:
        console.print(line.rstrip())


@app.command()
def collections():
    """List all collections"""
    config, db, indexer = get_app_state()
    from .commands.collections import list_collections
    list_collections(config, db)


@app.command()
def sync():
    """Sync with git remote"""
    config, db, indexer = get_app_state()
    from .commands.sync import do_sync
    do_sync(config, db, indexer)


@app.command()
def reindex(
    full: bool = typer.Option(False, "--full", help="Force full reindex"),
):
    """Rebuild the SQLite cache"""
    config, db, indexer = get_app_state()

    if full:
        count = indexer.full_reindex()
        console.print(f"[green]Full reindex complete:[/green] {count} files")
    else:
        count = indexer.incremental_reindex()
        if count > 0:
            console.print(f"[green]Reindexed:[/green] {count} files")
        else:
            console.print("[dim]No changes detected[/dim]")


@app.command()
def undo():
    """Undo the last action"""
    config, db, indexer = get_app_state()
    from .commands.undo import do_undo
    do_undo(config, db, indexer)


@app.command()
def edit(
    target: Optional[str] = typer.Argument(None, help="What to edit (today, date, month, future, collection name)"),
):
    """Open a file in your editor"""
    config, db, indexer = get_app_state()
    from .commands.editor import open_in_editor

    if not target or target.lower() in ("today", "t"):
        file_path = create_daily_file(config.data_dir, date.today())
    elif target.lower() == "future":
        file_path = create_future_file(config.data_dir)
    else:
        # Try as date
        parsed_date = parse_date(target)
        if parsed_date:
            file_path = create_daily_file(config.data_dir, parsed_date)
        else:
            # Try as month
            parsed_month = parse_month(target)
            if parsed_month:
                year, month_num = parsed_month
                file_path = create_monthly_file(config.data_dir, year, month_num)
            else:
                # Try as collection
                file_path = get_collection_file(config.data_dir, target)
                if not file_path.exists():
                    console.print(f"[red]Not found: {target}[/red]")
                    raise typer.Exit(1)

    open_in_editor(config, file_path)
    indexer.reindex_file(file_path)


@app.command()
def init():
    """Initialize a new bullet journal"""
    config, db, indexer = get_app_state()

    # Create directories
    ensure_data_dirs(config.data_dir)

    # Create config file if it doesn't exist
    if not config.config_file.exists():
        config.config_file.parent.mkdir(parents=True, exist_ok=True)
        config.config_file.write_text(get_default_config_yaml())
        console.print(f"[green]Created config:[/green] {config.config_file}")

    # Create initial files
    create_future_file(config.data_dir)
    create_daily_file(config.data_dir, date.today())

    today = date.today()
    create_monthly_file(config.data_dir, today.year, today.month)

    # Initialize git if not already
    git_dir = config.bujo_dir / ".git"
    if not git_dir.exists():
        import subprocess
        try:
            subprocess.run(["git", "init"], cwd=config.bujo_dir, capture_output=True)
            # Create .gitignore
            gitignore = config.bujo_dir / ".gitignore"
            gitignore.write_text("""# Local cache - never sync
cache.db
cache.db-journal
cache.db-wal
cache.db-shm

# Editor artifacts
*.swp
*~
.DS_Store
""")
            console.print("[green]Initialized git repository[/green]")
        except Exception:
            pass

    # Full index
    indexer.full_reindex()

    console.print()
    console.print("[bold green]Bullet journal initialized![/bold green]")
    console.print(f"  Location: {config.bujo_dir}")
    console.print()
    console.print("Run [bold]bujo[/bold] to start journaling.")


@app.command("export")
def export_cmd(
    format: str = typer.Option("html", "-f", "--format", help="Export format (html/pdf)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output file"),
    year: Optional[int] = typer.Option(None, "-y", "--year", help="Export specific year"),
    month_num: Optional[int] = typer.Option(None, "-m", "--month", help="Export specific month"),
):
    """Export journal to HTML or PDF"""
    config, db, indexer = get_app_state()
    from .commands.export import do_export
    do_export(config, db, format, output, year, month_num)


if __name__ == "__main__":
    app()
