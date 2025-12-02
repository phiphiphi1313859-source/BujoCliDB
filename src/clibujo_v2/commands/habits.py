"""Habit-related CLI commands for CLIBuJo v2."""

import click
from datetime import date, datetime
from calendar import monthrange

from ..core.db import ensure_db
from ..core.habits import (
    create_habit,
    get_habit,
    get_habit_by_name,
    get_all_habits,
    get_active_habits,
    update_habit,
    pause_habit,
    resume_habit,
    quit_habit,
    delete_habit,
    record_completion,
    remove_completion,
    is_completed_on_date,
    get_habits_due_on_date,
    get_habit_progress,
    get_habit_calendar,
    get_categories,
)
from .display import format_habit_status, format_habits_list
from .entries import parse_date_arg


@click.group()
def habits():
    """Manage habit tracking."""
    ensure_db()


@habits.command("list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all habits (not just active)")
@click.option("--category", "-c", help="Filter by category")
def list_habits(show_all: bool, category: str):
    """List habits."""
    if show_all:
        habit_list = get_all_habits(category=category)
    else:
        habit_list = get_all_habits(status="active", category=category)

    if not habit_list:
        click.echo("No habits found.")
        return

    today = date.today()
    today_str = today.isoformat()

    # Build progress and completion maps
    progress_map = {}
    completed_map = {}

    for h in habit_list:
        progress_map[h.id] = get_habit_progress(h, today)
        completed_map[h.id] = is_completed_on_date(h.id, today_str)

    output = format_habits_list(habit_list, progress_map, completed_map)
    click.echo(output)


@habits.command("add")
@click.argument("name")
@click.option("--frequency", "-f", default="daily",
              help="Frequency: daily, weekly, weekly:N, monthly:N, days:mon,wed,fri")
@click.option("--category", "-c", help="Category for grouping")
def add_habit(name: str, frequency: str, category: str):
    """Add a new habit."""
    try:
        habit = create_habit(name, frequency, category)
        click.echo(f"Created habit: {habit.name} ({habit.get_frequency_display()})")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise click.ClickException(f"Habit already exists: {name}")
        raise


@habits.command("done")
@click.argument("name_or_id")
@click.option("--date", "-d", "date_arg", default="today", help="Completion date")
@click.option("--note", "-n", help="Optional note")
def mark_done(name_or_id: str, date_arg: str, note: str):
    """Mark a habit as done for today (or a specific date)."""
    # Find habit
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    completion_date = parse_date_arg(date_arg)

    # Check if already completed
    if is_completed_on_date(habit.id, completion_date):
        click.echo(f"Already completed on {completion_date}")
        return

    record_completion(habit.id, completion_date, note)
    click.echo(f"Marked done: {habit.name} ({completion_date})")

    # Show streak
    progress = get_habit_progress(habit, datetime.strptime(completion_date, "%Y-%m-%d").date())
    if progress["streak"] > 1:
        click.echo(f"  Streak: {progress['streak']}")


@habits.command("undo")
@click.argument("name_or_id")
@click.option("--date", "-d", "date_arg", default="today", help="Date to undo")
def undo_done(name_or_id: str, date_arg: str):
    """Remove a habit completion for a date."""
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    completion_date = parse_date_arg(date_arg)

    if remove_completion(habit.id, completion_date):
        click.echo(f"Removed completion: {habit.name} ({completion_date})")
    else:
        click.echo(f"No completion found for {completion_date}")


@habits.command("status")
@click.argument("name_or_id")
def status(name_or_id: str):
    """Show detailed status for a habit."""
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    today = date.today()
    progress = get_habit_progress(habit, today)
    completed = is_completed_on_date(habit.id, today.isoformat())

    click.echo(f"\n== {habit.name} ==")
    click.echo(f"Frequency: {habit.get_frequency_display()}")
    click.echo(f"Status: {habit.status}")
    if habit.category:
        click.echo(f"Category: {habit.category}")
    click.echo()

    # Current period progress
    click.echo(f"This {progress['period']}:")
    click.echo(f"  Completed: {progress['completed']}/{progress['target']}")
    click.echo(f"  Progress: {progress['percentage']}%")
    click.echo(f"  Streak: {progress['streak']}")
    click.echo()

    # Today's status
    today_status = "[x] Done today" if completed else "[ ] Not done today"
    click.echo(today_status)


@habits.command("calendar")
@click.argument("name_or_id")
@click.option("--month", "-m", help="Month to show (YYYY-MM), defaults to current")
def calendar(name_or_id: str, month: str):
    """Show habit completion calendar for a month."""
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    if month:
        year, mon = map(int, month.split("-"))
    else:
        today = date.today()
        year, mon = today.year, today.month

    cal = get_habit_calendar(habit.id, year, mon)
    days_in_month = monthrange(year, mon)[1]

    # Get month name
    month_name = date(year, mon, 1).strftime("%B %Y")

    click.echo(f"\n== {habit.name}: {month_name} ==\n")

    # Simple calendar grid
    click.echo(" Mo Tu We Th Fr Sa Su")

    # Find what day the month starts on
    first_day = date(year, mon, 1).weekday()  # 0=Monday

    # Print leading spaces
    row = " " + "   " * first_day

    for day in range(1, days_in_month + 1):
        completed = cal.get(day, False)
        mark = " X" if completed else " ."
        row += f"{mark:>3}"

        # Check if end of week
        day_of_week = (first_day + day - 1) % 7
        if day_of_week == 6:
            click.echo(row)
            row = " "

    # Print remaining days
    if row.strip():
        click.echo(row)

    # Summary
    completed_count = sum(1 for v in cal.values() if v)
    click.echo(f"\nCompleted: {completed_count}/{days_in_month} days")


@habits.command("edit")
@click.argument("name_or_id")
@click.option("--name", "-n", "new_name", help="New name")
@click.option("--frequency", "-f", help="New frequency")
@click.option("--category", "-c", help="New category")
def edit_habit(name_or_id: str, new_name: str, frequency: str, category: str):
    """Edit a habit."""
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    updated = update_habit(
        habit.id,
        name=new_name,
        frequency=frequency,
        category=category,
    )

    if updated:
        click.echo(f"Updated: {updated.name} ({updated.get_frequency_display()})")


@habits.command("pause")
@click.argument("name_or_id")
def pause(name_or_id: str):
    """Pause a habit (temporarily stop tracking)."""
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    updated = pause_habit(habit.id)
    if updated:
        click.echo(f"Paused: {updated.name}")


@habits.command("resume")
@click.argument("name_or_id")
def resume(name_or_id: str):
    """Resume a paused habit."""
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    updated = resume_habit(habit.id)
    if updated:
        click.echo(f"Resumed: {updated.name}")


@habits.command("quit")
@click.argument("name_or_id")
def quit_cmd(name_or_id: str):
    """Quit a habit (mark as intentionally stopped, e.g., bad habit you're breaking)."""
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    updated = quit_habit(habit.id)
    if updated:
        click.echo(f"Quit: {updated.name}")


@habits.command("delete")
@click.argument("name_or_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete(name_or_id: str, yes: bool):
    """Delete a habit and all its history."""
    try:
        habit_id = int(name_or_id)
        habit = get_habit(habit_id)
    except ValueError:
        habit = get_habit_by_name(name_or_id)

    if not habit:
        raise click.ClickException(f"Habit not found: {name_or_id}")

    if not yes:
        click.confirm(f"Delete '{habit.name}' and all completion history?", abort=True)

    if delete_habit(habit.id):
        click.echo(f"Deleted: {habit.name}")


@habits.command("today")
def today():
    """Show habits due today."""
    today_date = date.today()
    habits_due = get_habits_due_on_date(today_date)

    if not habits_due:
        click.echo("No habits due today.")
        return

    click.echo(f"\n== Habits for {today_date.isoformat()} ==\n")

    for habit in habits_due:
        completed = is_completed_on_date(habit.id, today_date.isoformat())
        progress = get_habit_progress(habit, today_date)
        line = format_habit_status(habit, progress, completed)
        click.echo(f"  {line}")


@habits.command("categories")
def list_categories():
    """List all habit categories."""
    cats = get_categories()

    if not cats:
        click.echo("No categories found.")
        return

    click.echo("\nCategories:")
    for cat in cats:
        count = len(get_all_habits(category=cat))
        click.echo(f"  {cat} ({count} habits)")
