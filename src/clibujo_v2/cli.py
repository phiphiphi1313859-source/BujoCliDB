"""Main CLI for CLIBuJo v2."""

import click
from datetime import date

from . import __version__
from .core.db import ensure_db, init_db
from .core.entries import get_entries_by_date, create_entry
from .core.habits import get_habits_due_on_date, is_completed_on_date, record_completion, get_habit_by_name
from .core.collections import get_collection_by_name
from .core.undo import undo_last_action
from .commands.entries import entries, parse_date_arg, parse_signifier
from .commands.collections import collections
from .commands.habits import habits
from .commands.migrate import migrate
from .commands.undo import undo, undo_shortcut
from .commands.export import export
from .commands.sync import sync
from .commands.migrate_v1 import import_v1
from .commands.mood import mood
from .commands.display import format_daily_log, format_entry


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version")
@click.pass_context
def cli(ctx, version):
    """CLIBuJo v2 - SQLite-first CLI Bullet Journal.

    Run without arguments to view today's log.
    """
    ensure_db()

    if version:
        click.echo(f"CLIBuJo v{__version__}")
        return

    if ctx.invoked_subcommand is None:
        # Default: show today's log
        ctx.invoke(view_today)


@cli.command("today")
def view_today():
    """View today's log (default command)."""
    today = date.today().isoformat()
    entries = get_entries_by_date(today)

    # Get habits
    habits_data = []
    try:
        habits_due = get_habits_due_on_date()
        for habit in habits_due:
            completed = is_completed_on_date(habit.id, today)
            habits_data.append({"habit": habit, "completed": completed})
    except Exception:
        pass

    output = format_daily_log(today, entries, habits_data)
    click.echo(output)


# Quick add commands
@cli.command("add")
@click.argument("content", nargs=-1, required=True)
@click.option("--date", "-d", "date_arg", default=None, help="Date for entry")
@click.option("--type", "-t", "entry_type", type=click.Choice(["task", "event", "note"]), default="task")
@click.option("--collection", "-c", "collection_name", help="Add to collection")
@click.option("--month", "-m", "month_arg", help="Add to monthly log (YYYY-MM)")
@click.option("--priority", "-p", is_flag=True, help="Mark as priority")
def quick_add(content, date_arg, entry_type, collection_name, month_arg, priority):
    """Quick add an entry to today."""
    text = " ".join(content)
    signifier, text = parse_signifier(text)

    if priority:
        signifier = "priority"

    # Resolve collection
    collection_id = None
    if collection_name:
        coll = get_collection_by_name(collection_name)
        if not coll:
            raise click.ClickException(f"Collection not found: {collection_name}")
        collection_id = coll.id

    # Determine entry_date vs entry_month
    entry_date = None
    entry_month = None

    if month_arg:
        entry_month = month_arg
    elif collection_id and not date_arg:
        # Adding to collection without date - no date needed
        pass
    else:
        entry_date = parse_date_arg(date_arg or "today")

    entry = create_entry(
        content=text,
        entry_type=entry_type,
        entry_date=entry_date,
        entry_month=entry_month,
        collection_id=collection_id,
        signifier=signifier,
    )

    click.echo(f"Added: {format_entry(entry)}")


@cli.command("done")
@click.argument("identifier")
def quick_done(identifier: str):
    """Mark a task or habit as done.

    IDENTIFIER can be an entry ID (number) or habit name.
    """
    # Try as entry ID first
    try:
        entry_id = int(identifier)
        from .core.entries import complete_entry

        entry = complete_entry(entry_id)
        if entry:
            click.echo(f"Completed: {format_entry(entry)}")
        else:
            raise click.ClickException(f"Entry not found or not a task: {entry_id}")
        return
    except ValueError:
        pass

    # Try as habit name
    habit = get_habit_by_name(identifier)
    if habit:
        today = date.today().isoformat()
        if is_completed_on_date(habit.id, today):
            click.echo(f"Already done today: {habit.name}")
        else:
            record_completion(habit.id, today)
            click.echo(f"Marked done: {habit.name}")
        return

    raise click.ClickException(f"Not found: {identifier}")


@cli.command("view")
@click.argument("date_arg", default="today")
def view_day(date_arg: str):
    """View a day's log.

    DATE_ARG: today, tomorrow, yesterday, +N, -N, YYYY-MM-DD, MM-DD
    """
    entry_date = parse_date_arg(date_arg)
    entries = get_entries_by_date(entry_date)

    # Get habits if viewing today
    habits_data = []
    if entry_date == date.today().isoformat():
        try:
            habits_due = get_habits_due_on_date()
            for habit in habits_due:
                completed = is_completed_on_date(habit.id, entry_date)
                habits_data.append({"habit": habit, "completed": completed})
        except Exception:
            pass

    output = format_daily_log(entry_date, entries, habits_data)
    click.echo(output)


@cli.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=20, help="Max results")
def quick_search(query: str, limit: int):
    """Search entries."""
    from .core.entries import search_entries
    from .commands.display import format_search_results

    results = search_entries(query, limit=limit)
    output = format_search_results(results, query)
    click.echo(output)


@cli.command("init")
def init():
    """Initialize the database."""
    init_db()
    click.echo("Database initialized.")


@cli.command("interactive")
def interactive():
    """Start interactive mode."""
    from .interactive import run_interactive
    run_interactive()


# Add undo shortcut at top level
cli.add_command(undo_shortcut, name="undo")

# Register command groups
cli.add_command(entries)
cli.add_command(collections)
cli.add_command(habits)
cli.add_command(migrate)
cli.add_command(undo, name="undo-history")
cli.add_command(export)
cli.add_command(sync)
cli.add_command(import_v1)
cli.add_command(mood)


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
