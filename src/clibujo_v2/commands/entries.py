"""Entry-related CLI commands for CLIBuJo v2."""

import click
from datetime import date, datetime, timedelta
from typing import Optional

from ..core.db import ensure_db
from ..core.entries import (
    create_entry,
    get_entry,
    get_entries_by_date,
    get_entries_by_month,
    get_entries_by_collection,
    get_open_tasks,
    update_entry,
    complete_entry,
    cancel_entry,
    reopen_entry,
    delete_entry,
    search_entries,
    get_entries_date_range,
)
from ..core.collections import get_collection_by_name
from ..core.habits import get_habits_due_on_date, is_completed_on_date, get_habit_progress
from ..core.models import SIGNIFIER_FROM_SYMBOL
from .display import format_entry, format_daily_log, format_entry_list, format_search_results


def parse_signifier(text: str) -> tuple:
    """Parse signifier from start of text.

    Returns (signifier, remaining_text).
    """
    if text and text[0] in SIGNIFIER_FROM_SYMBOL:
        return SIGNIFIER_FROM_SYMBOL[text[0]], text[1:].strip()
    return None, text


def parse_date_arg(date_arg: Optional[str]) -> str:
    """Parse date argument into YYYY-MM-DD.

    Supports: today, tomorrow, yesterday, +N, -N, YYYY-MM-DD, MM-DD
    """
    if not date_arg or date_arg.lower() == "today":
        return date.today().isoformat()

    if date_arg.lower() == "tomorrow":
        return (date.today() + timedelta(days=1)).isoformat()

    if date_arg.lower() == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()

    if date_arg.startswith("+"):
        days = int(date_arg[1:])
        return (date.today() + timedelta(days=days)).isoformat()

    if date_arg.startswith("-"):
        days = int(date_arg[1:])
        return (date.today() - timedelta(days=days)).isoformat()

    # Try YYYY-MM-DD
    try:
        datetime.strptime(date_arg, "%Y-%m-%d")
        return date_arg
    except ValueError:
        pass

    # Try MM-DD (assume current year)
    try:
        parsed = datetime.strptime(date_arg, "%m-%d")
        return parsed.replace(year=date.today().year).strftime("%Y-%m-%d")
    except ValueError:
        pass

    raise click.BadParameter(f"Invalid date format: {date_arg}")


@click.group()
def entries():
    """Manage bullet journal entries."""
    ensure_db()


@entries.command("view")
@click.argument("date_arg", default="today")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all entry types")
def view_day(date_arg: str, show_all: bool):
    """View daily log for a date.

    DATE_ARG can be: today, tomorrow, yesterday, +N, -N, YYYY-MM-DD, MM-DD
    """
    entry_date = parse_date_arg(date_arg)
    entries = get_entries_by_date(entry_date)

    # Get habits due today
    habits_data = []
    try:
        target = datetime.strptime(entry_date, "%Y-%m-%d").date()
        habits = get_habits_due_on_date(target)
        for habit in habits:
            completed = is_completed_on_date(habit.id, entry_date)
            habits_data.append({"habit": habit, "completed": completed})
    except Exception:
        pass

    output = format_daily_log(entry_date, entries, habits_data)
    click.echo(output)


@entries.command("add")
@click.argument("content", nargs=-1, required=True)
@click.option("--date", "-d", "date_arg", default="today", help="Date for entry")
@click.option("--type", "-t", "entry_type", type=click.Choice(["task", "event", "note"]), default="task")
@click.option("--collection", "-c", "collection_name", help="Add to collection")
@click.option("--month", "-m", "month_arg", help="Add to monthly log (YYYY-MM)")
@click.option("--priority", "-p", is_flag=True, help="Mark as priority")
def add_entry(content, date_arg, entry_type, collection_name, month_arg, priority):
    """Add a new entry.

    Content can start with a signifier: * ! ? @ #
    """
    text = " ".join(content)
    signifier, text = parse_signifier(text)

    if priority:
        signifier = "priority"

    collection_id = None
    if collection_name:
        coll = get_collection_by_name(collection_name)
        if not coll:
            raise click.ClickException(f"Collection not found: {collection_name}")
        collection_id = coll.id

    entry_date = None
    entry_month = None

    if month_arg:
        entry_month = month_arg
    elif not collection_name:
        entry_date = parse_date_arg(date_arg)

    entry = create_entry(
        content=text,
        entry_type=entry_type,
        entry_date=entry_date,
        entry_month=entry_month,
        collection_id=collection_id,
        signifier=signifier,
    )

    click.echo(f"Added: {format_entry(entry)}")


@entries.command("complete")
@click.argument("entry_id", type=int)
def complete_task(entry_id: int):
    """Mark a task as complete."""
    entry = complete_entry(entry_id)
    if entry:
        click.echo(f"Completed: {format_entry(entry)}")
    else:
        raise click.ClickException(f"Entry not found or not a task: {entry_id}")


@entries.command("cancel")
@click.argument("entry_id", type=int)
def cancel_task(entry_id: int):
    """Cancel a task."""
    entry = cancel_entry(entry_id)
    if entry:
        click.echo(f"Cancelled: {format_entry(entry)}")
    else:
        raise click.ClickException(f"Entry not found or not a task: {entry_id}")


@entries.command("reopen")
@click.argument("entry_id", type=int)
def reopen_task(entry_id: int):
    """Reopen a completed/cancelled task."""
    entry = reopen_entry(entry_id)
    if entry:
        click.echo(f"Reopened: {format_entry(entry)}")
    else:
        raise click.ClickException(f"Entry not found: {entry_id}")


@entries.command("edit")
@click.argument("entry_id", type=int)
@click.argument("new_content", nargs=-1)
@click.option("--signifier", "-s", help="Set signifier (priority, inspiration, explore, waiting, delegated, or empty)")
def edit_entry(entry_id: int, new_content, signifier):
    """Edit an entry's content or signifier."""
    content = " ".join(new_content) if new_content else None

    # Parse signifier from content if present
    if content:
        parsed_signifier, content = parse_signifier(content)
        if parsed_signifier:
            signifier = parsed_signifier

    entry = update_entry(
        entry_id,
        content=content if content else None,
        signifier=signifier,
    )

    if entry:
        click.echo(f"Updated: {format_entry(entry)}")
    else:
        raise click.ClickException(f"Entry not found: {entry_id}")


@entries.command("delete")
@click.argument("entry_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete_entry_cmd(entry_id: int, yes: bool):
    """Delete an entry."""
    entry = get_entry(entry_id)
    if not entry:
        raise click.ClickException(f"Entry not found: {entry_id}")

    if not yes:
        click.confirm(f"Delete '{entry.content}'?", abort=True)

    if delete_entry(entry_id):
        click.echo(f"Deleted entry #{entry_id}")
    else:
        raise click.ClickException("Failed to delete entry")


@entries.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=20, help="Max results")
def search(query: str, limit: int):
    """Search entries using full-text search."""
    results = search_entries(query, limit=limit)
    output = format_search_results(results, query)
    click.echo(output)


@entries.command("open")
@click.option("--before", "-b", "before_date", help="Show open tasks before this date")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all open tasks")
def list_open(before_date: Optional[str], show_all: bool):
    """List open tasks that may need attention."""
    if show_all:
        tasks = get_open_tasks()
    else:
        if before_date:
            target = parse_date_arg(before_date)
        else:
            target = date.today().isoformat()
        tasks = get_open_tasks(before_date=target)

    output = format_entry_list(tasks, title="Open Tasks")
    click.echo(output)


@entries.command("week")
@click.option("--offset", "-o", default=0, help="Week offset (0=this week, -1=last week)")
def view_week(offset: int):
    """View entries for the week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)

    click.echo(f"== Week of {monday.isoformat()} ==\n")

    for i in range(7):
        day = monday + timedelta(days=i)
        day_str = day.isoformat()
        entries = get_entries_by_date(day_str)

        if entries:
            day_name = day.strftime("%A")
            click.echo(f"{day_name} ({day_str}):")
            for entry in entries:
                click.echo(f"  {format_entry(entry)}")
            click.echo()


@entries.command("month")
@click.argument("month_arg", default=None, required=False)
def view_month(month_arg: Optional[str]):
    """View monthly log entries.

    MONTH_ARG: YYYY-MM format, defaults to current month
    """
    if month_arg:
        target_month = month_arg
    else:
        target_month = date.today().strftime("%Y-%m")

    entries = get_entries_by_month(target_month)
    output = format_entry_list(entries, title=f"Monthly Log: {target_month}")
    click.echo(output)
