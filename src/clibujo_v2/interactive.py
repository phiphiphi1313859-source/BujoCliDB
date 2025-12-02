"""Interactive mode for CLIBuJo v2."""

import sys
from datetime import date, datetime, timedelta

from .core.db import ensure_db
from .core.entries import (
    create_entry,
    get_entries_by_date,
    complete_entry,
    cancel_entry,
    reopen_entry,
    delete_entry,
    search_entries,
    get_entry,
)
from .core.collections import get_all_collections, get_collection_by_name
from .core.habits import (
    get_habits_due_on_date,
    is_completed_on_date,
    record_completion,
    remove_completion,
    get_habit_by_name,
    get_active_habits,
    get_habit_progress,
)
from .core.migrations import migrate_forward, get_tasks_needing_migration
from .core.undo import undo_last_action, get_undo_preview
from .commands.display import (
    format_entry,
    format_daily_log,
    format_entry_list,
    format_search_results,
)
from .commands.entries import parse_signifier

HELP_TEXT = """
CLIBuJo Interactive Mode
========================

Commands:
  <text>           Add a task with the given text
  e <text>         Add an event
  n <text>         Add a note

  x <id>           Complete a task
  ~ <id>           Cancel a task
  o <id>           Reopen a task
  d <id>           Delete an entry

  h <name>         Mark habit as done
  hu <name>        Undo habit completion

  > <id>           Migrate task to today

  t, today         View today's log
  y, yesterday     View yesterday
  +N, -N           View N days forward/back

  s <query>        Search entries
  open             Show open tasks needing migration

  u, undo          Undo last action
  uh               Show undo history

  c, collections   List collections
  habits           List habits

  q, quit, exit    Exit interactive mode
  ?, help          Show this help

Signifiers (prefix to entry text):
  * priority   ! inspiration   ? explore
  @ waiting    # delegated
"""


def show_view(view_date: date):
    """Display the daily log for a date."""
    date_str = view_date.isoformat()
    entries = get_entries_by_date(date_str)

    # Get habits if viewing today
    habits_data = []
    if view_date == date.today():
        try:
            habits_due = get_habits_due_on_date(view_date)
            for habit in habits_due:
                completed = is_completed_on_date(habit.id, date_str)
                habits_data.append({"habit": habit, "completed": completed})
        except Exception:
            pass

    output = format_daily_log(date_str, entries, habits_data)
    print(output)


def process_command(cmd: str, current_date: date) -> date:
    """Process a command and return the (possibly updated) current date."""
    cmd = cmd.strip()

    if not cmd:
        return current_date

    # Navigation commands
    if cmd in ("t", "today"):
        current_date = date.today()
        show_view(current_date)
        return current_date

    if cmd in ("y", "yesterday"):
        current_date = date.today() - timedelta(days=1)
        show_view(current_date)
        return current_date

    if cmd.startswith("+") and cmd[1:].isdigit():
        days = int(cmd[1:])
        current_date = date.today() + timedelta(days=days)
        show_view(current_date)
        return current_date

    if cmd.startswith("-") and cmd[1:].isdigit():
        days = int(cmd[1:])
        current_date = date.today() - timedelta(days=days)
        show_view(current_date)
        return current_date

    # Help
    if cmd in ("?", "help"):
        print(HELP_TEXT)
        return current_date

    # Quit
    if cmd in ("q", "quit", "exit"):
        print("Goodbye!")
        sys.exit(0)

    # Undo
    if cmd in ("u", "undo"):
        result = undo_last_action()
        if result["success"]:
            print(f"Undone: {result['message']}")
        else:
            print(result["message"])
        return current_date

    if cmd == "uh":
        descriptions = get_undo_preview(5)
        if descriptions:
            print("Recent actions:")
            for i, desc in enumerate(descriptions, 1):
                print(f"  {i}. {desc}")
        else:
            print("No actions to undo")
        return current_date

    # Task completion: x <id>
    if cmd.startswith("x "):
        try:
            entry_id = int(cmd[2:].strip())
            entry = complete_entry(entry_id)
            if entry:
                print(f"Completed: {format_entry(entry)}")
            else:
                print(f"Not found or not a task: {entry_id}")
        except ValueError:
            print("Usage: x <entry_id>")
        return current_date

    # Task cancel: ~ <id>
    if cmd.startswith("~ "):
        try:
            entry_id = int(cmd[2:].strip())
            entry = cancel_entry(entry_id)
            if entry:
                print(f"Cancelled: {format_entry(entry)}")
            else:
                print(f"Not found or not a task: {entry_id}")
        except ValueError:
            print("Usage: ~ <entry_id>")
        return current_date

    # Task reopen: o <id>
    if cmd.startswith("o "):
        try:
            entry_id = int(cmd[2:].strip())
            entry = reopen_entry(entry_id)
            if entry:
                print(f"Reopened: {format_entry(entry)}")
            else:
                print(f"Not found: {entry_id}")
        except ValueError:
            print("Usage: o <entry_id>")
        return current_date

    # Delete: d <id>
    if cmd.startswith("d "):
        try:
            entry_id = int(cmd[2:].strip())
            entry = get_entry(entry_id)
            if entry:
                if delete_entry(entry_id):
                    print(f"Deleted: {entry.content}")
                else:
                    print("Delete failed")
            else:
                print(f"Not found: {entry_id}")
        except ValueError:
            print("Usage: d <entry_id>")
        return current_date

    # Migrate forward: > <id>
    if cmd.startswith("> "):
        try:
            entry_id = int(cmd[2:].strip())
            new_entry = migrate_forward(entry_id)
            if new_entry:
                print(f"Migrated to today: {format_entry(new_entry)}")
            else:
                print(f"Cannot migrate: {entry_id}")
        except ValueError:
            print("Usage: > <entry_id>")
        return current_date

    # Habit done: h <name>
    if cmd.startswith("h "):
        name = cmd[2:].strip()
        habit = get_habit_by_name(name)
        if habit:
            today_str = date.today().isoformat()
            if is_completed_on_date(habit.id, today_str):
                print(f"Already done today: {habit.name}")
            else:
                record_completion(habit.id, today_str)
                print(f"Marked done: {habit.name}")
        else:
            print(f"Habit not found: {name}")
        return current_date

    # Habit undo: hu <name>
    if cmd.startswith("hu "):
        name = cmd[3:].strip()
        habit = get_habit_by_name(name)
        if habit:
            today_str = date.today().isoformat()
            if remove_completion(habit.id, today_str):
                print(f"Removed completion: {habit.name}")
            else:
                print(f"No completion today: {habit.name}")
        else:
            print(f"Habit not found: {name}")
        return current_date

    # Search: s <query>
    if cmd.startswith("s "):
        query = cmd[2:].strip()
        results = search_entries(query)
        output = format_search_results(results, query)
        print(output)
        return current_date

    # Show open tasks
    if cmd == "open":
        tasks = get_tasks_needing_migration()
        output = format_entry_list(tasks, title="Open Tasks (need migration)")
        print(output)
        return current_date

    # List collections
    if cmd in ("c", "collections"):
        colls = get_all_collections()
        if colls:
            print("\nCollections:")
            for c in colls:
                print(f"  [{c.id}] {c.name} ({c.type})")
        else:
            print("No collections")
        return current_date

    # List habits
    if cmd == "habits":
        habits_list = get_active_habits()
        if habits_list:
            print("\nHabits:")
            today_d = date.today()
            today_str = today_d.isoformat()
            for h in habits_list:
                completed = is_completed_on_date(h.id, today_str)
                progress = get_habit_progress(h, today_d)
                status = "[x]" if completed else "[ ]"
                streak = f" (streak: {progress['streak']})" if progress['streak'] > 0 else ""
                print(f"  {status} {h.name} ({h.get_frequency_display()}){streak}")
        else:
            print("No active habits")
        return current_date

    # Add event: e <text>
    if cmd.startswith("e "):
        text = cmd[2:].strip()
        signifier, text = parse_signifier(text)
        entry = create_entry(
            content=text,
            entry_type="event",
            entry_date=current_date.isoformat(),
            signifier=signifier,
        )
        print(f"Added: {format_entry(entry)}")
        return current_date

    # Add note: n <text>
    if cmd.startswith("n "):
        text = cmd[2:].strip()
        signifier, text = parse_signifier(text)
        entry = create_entry(
            content=text,
            entry_type="note",
            entry_date=current_date.isoformat(),
            signifier=signifier,
        )
        print(f"Added: {format_entry(entry)}")
        return current_date

    # Default: add task
    signifier, text = parse_signifier(cmd)
    entry = create_entry(
        content=text,
        entry_type="task",
        entry_date=current_date.isoformat(),
        signifier=signifier,
    )
    print(f"Added: {format_entry(entry)}")
    return current_date


def run_interactive():
    """Run the interactive mode."""
    ensure_db()

    print("CLIBuJo v2 Interactive Mode")
    print("Type '?' for help, 'q' to quit\n")

    current_date = date.today()
    show_view(current_date)

    while True:
        try:
            prompt = f"\n[{current_date.isoformat()}] > "
            cmd = input(prompt)
            current_date = process_command(cmd, current_date)
        except EOFError:
            print("\nGoodbye!")
            break
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    run_interactive()
