"""Interactive mode for CLIBuJo"""

from datetime import date, datetime
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

from ..core.config import Config
from ..core.database import Database
from ..core.indexer import Indexer
from ..core.models import EntryType, TaskStatus, Signifier, UndoAction
from ..core.parser import parse_entry, update_task_status
from ..utils.files import (
    create_daily_file,
    read_file_lines,
    append_line,
    update_line,
    get_daily_file,
)
from ..utils.dates import format_date, format_short_date
from ..utils.display import get_terminal_width, is_narrow_terminal, truncate

console = Console()


def interactive_mode(config: Config, db: Database, indexer: Indexer):
    """Run interactive mode"""
    session = PromptSession(history=InMemoryHistory())
    today = date.today()
    current_date = today

    while True:
        try:
            # Display current day
            _display_day(config, db, current_date)

            # Show command bar
            _show_command_bar(config)

            # Get input
            try:
                user_input = session.prompt("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue

            # Parse command
            cmd = user_input[0].lower()
            args = user_input[1:].strip()

            if cmd == "q":
                break
            elif cmd == "a":
                _cmd_add(config, db, indexer, current_date, args)
            elif cmd == "x":
                _cmd_complete(config, db, indexer, current_date, args)
            elif cmd == ">":
                _cmd_migrate(config, db, indexer, current_date, args)
            elif cmd == "~":
                _cmd_cancel(config, db, indexer, current_date, args)
            elif cmd == "c":
                _cmd_collections(config, db)
            elif cmd == "m":
                _cmd_month(config, db, current_date)
            elif cmd == "f":
                _cmd_future(config, db)
            elif cmd == "/":
                _cmd_search(config, db, args)
            elif cmd == "s":
                _cmd_sync(config, db, indexer)
            elif cmd == "e":
                _cmd_edit(config, indexer, current_date)
            elif cmd == "u":
                _cmd_undo(config, db, indexer)
            elif cmd == "d":
                # Change date
                from ..utils.dates import parse_date
                if args:
                    new_date = parse_date(args)
                    if new_date:
                        current_date = new_date
                    else:
                        console.print(f"[red]Invalid date: {args}[/red]")
                else:
                    current_date = today
            elif cmd == "?":
                _show_help()
            elif user_input.startswith("[ ]") or user_input.startswith("["):
                # Quick add with prefix
                _quick_add(config, db, indexer, current_date, user_input)
            elif user_input.startswith("○") or user_input.startswith("-"):
                _quick_add(config, db, indexer, current_date, user_input)
            elif user_input.startswith("* ") or user_input.startswith("! ") or user_input.startswith("? "):
                _quick_add(config, db, indexer, current_date, user_input)
            else:
                console.print(f"[dim]Unknown command. Type ? for help.[/dim]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def _display_day(config: Config, db: Database, target_date: date):
    """Display a day's entries"""
    console.clear()
    width = get_terminal_width()
    narrow = is_narrow_terminal(config.narrow_threshold)

    # Header
    date_str = format_date(target_date, config.date_format)
    is_today = target_date == date.today()

    if narrow:
        header = format_short_date(target_date)
        if is_today:
            header += " [TODAY]"
        console.print(f"[bold]{header}[/bold]")
    else:
        console.print()
        title = "CLIBuJo"
        if is_today:
            title += " [TODAY]"
        padding = width - len(title) - len(date_str)
        console.print(f"[bold]{title}[/bold]" + " " * max(1, padding) + date_str)
        console.print()
        console.print("═" * min(width, 60))

    console.print()

    # Get entries
    file_path = get_daily_file(config.data_dir, target_date)
    if not file_path.exists():
        console.print("[dim](empty day — start logging!)[/dim]")
        console.print()
        return

    rel_path = str(file_path.relative_to(config.data_dir))
    entries = db.get_entries_by_file(rel_path)

    if not entries:
        console.print("[dim](empty day — start logging!)[/dim]")
        console.print()
        return

    # Display entries
    task_index = 1
    for entry in entries:
        line = _format_entry(entry, task_index, config.show_entry_refs, width if narrow else None)
        console.print(line)
        if entry.entry_type == "task":
            task_index += 1

    console.print()


def _format_entry(entry, task_index: int, show_refs: bool, max_width: Optional[int] = None) -> str:
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
        status_map = {
            "open": "[ ]",
            "complete": "[x]",
            "migrated": "[>]",
            "scheduled": "[<]",
            "cancelled": "[~]",
        }
        parts.append(status_map.get(entry.status, "[ ]"))

        # Index
        if show_refs:
            parts.append(f"[{entry.entry_ref}]")
        else:
            parts.append(f"[{task_index}]")
    elif entry.entry_type == "event":
        parts.append("○  ")
        parts.append("   ")
    elif entry.entry_type == "note":
        parts.append("-  ")
        parts.append("   ")

    # Content
    parts.append(entry.content)

    line = " ".join(parts)
    if max_width:
        line = truncate(line, max_width)

    return line


def _show_command_bar(config: Config):
    """Show the command bar"""
    narrow = is_narrow_terminal(config.narrow_threshold)
    if narrow:
        console.print("[dim]a:add x:done >:migrate /:search s:sync q:quit ?:help[/dim]")
    else:
        console.print("─" * min(get_terminal_width(), 60))
        console.print("[dim][a]dd [x]complete [>]migrate [~]cancel [c]ollection [m]onth [f]uture [/]search [s]ync [e]dit [q]uit[/dim]")
    console.print()


def _cmd_add(config: Config, db: Database, indexer: Indexer, current_date: date, args: str):
    """Add command"""
    if args:
        # Type specified inline
        entry_type = args[0].lower()
        text = args[1:].strip()
    else:
        # Prompt for type
        console.print("Type [t]ask [e]vent [n]ote: ", end="")
        try:
            type_input = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            return

        if type_input in ("t", "task"):
            entry_type = "t"
        elif type_input in ("e", "event"):
            entry_type = "e"
        elif type_input in ("n", "note"):
            entry_type = "n"
        else:
            console.print("[red]Invalid type[/red]")
            return

        # Ask for priority if task
        priority = False
        if entry_type == "t":
            console.print("Priority? [y/N]: ", end="")
            try:
                priority = input().strip().lower() in ("y", "yes")
            except (EOFError, KeyboardInterrupt):
                return

        # Get content
        console.print("> ", end="")
        try:
            text = input().strip()
        except (EOFError, KeyboardInterrupt):
            return

        if priority:
            text = "* " + text

    if not text:
        return

    # Build line
    if entry_type == "t":
        if text.startswith("* "):
            line = "* [ ] " + text[2:]
        else:
            line = "[ ] " + text
    elif entry_type == "e":
        line = "○ " + text
    elif entry_type == "n":
        line = "- " + text
    else:
        line = "[ ] " + text

    # Add to file
    file_path = create_daily_file(config.data_dir, current_date)
    append_line(file_path, line)
    indexer.reindex_file(file_path)

    console.print(f"[green]Added:[/green] {line}")
    _pause()


def _quick_add(config: Config, db: Database, indexer: Indexer, current_date: date, text: str):
    """Quick add with prefix detection"""
    file_path = create_daily_file(config.data_dir, current_date)
    append_line(file_path, text)
    indexer.reindex_file(file_path)
    console.print(f"[green]Added:[/green] {text}")
    _pause()


def _cmd_complete(config: Config, db: Database, indexer: Indexer, current_date: date, args: str):
    """Complete a task"""
    if not args:
        console.print("Task number: ", end="")
        try:
            args = input().strip()
        except (EOFError, KeyboardInterrupt):
            return

    _update_task(config, db, indexer, current_date, args, TaskStatus.COMPLETE)


def _cmd_cancel(config: Config, db: Database, indexer: Indexer, current_date: date, args: str):
    """Cancel a task"""
    if not args:
        console.print("Task number: ", end="")
        try:
            args = input().strip()
        except (EOFError, KeyboardInterrupt):
            return

    _update_task(config, db, indexer, current_date, args, TaskStatus.CANCELLED)


def _update_task(
    config: Config,
    db: Database,
    indexer: Indexer,
    current_date: date,
    ref: str,
    new_status: TaskStatus,
):
    """Update task status"""
    file_path = get_daily_file(config.data_dir, current_date)
    rel_path = str(file_path.relative_to(config.data_dir))

    # Find the entry
    entry = None

    # Try as number
    try:
        idx = int(ref)
        entries = db.get_entries_by_file(rel_path)
        tasks = [e for e in entries if e.entry_type == "task"]
        if 1 <= idx <= len(tasks):
            entry = tasks[idx - 1]
    except ValueError:
        # Try as ref
        entry = db.get_entry_by_ref(ref)
        if not entry:
            entry = db.get_entry_by_ref_prefix(ref)

    if not entry:
        console.print(f"[red]Task not found: {ref}[/red]")
        _pause()
        return

    # Update file
    old_line = update_line(
        config.data_dir / entry.source_file,
        entry.line_number,
        update_task_status(entry.raw_line, new_status),
    )

    # Record undo
    if old_line:
        db.add_undo_action(UndoAction(
            action_type="edit",
            file_path=str(config.data_dir / entry.source_file),
            line_number=entry.line_number,
            old_content=old_line,
            new_content=update_task_status(entry.raw_line, new_status),
        ))

    # Update db
    completed_at = datetime.now() if new_status == TaskStatus.COMPLETE else None
    db.update_entry_status(entry.entry_ref, new_status.value, completed_at)

    indexer.reindex_file(config.data_dir / entry.source_file)

    status_str = new_status.value.capitalize()
    console.print(f"[green]{status_str}:[/green] {entry.content}")
    _pause()


def _cmd_migrate(config: Config, db: Database, indexer: Indexer, current_date: date, args: str):
    """Migrate a task"""
    if not args:
        console.print("Task number: ", end="")
        try:
            args = input().strip()
        except (EOFError, KeyboardInterrupt):
            return

    from .migrate import migrate_task
    migrate_task(config, db, indexer, args, None)
    _pause()


def _cmd_collections(config: Config, db: Database):
    """Show collections"""
    from .collections import list_collections
    list_collections(config, db)
    _pause()


def _cmd_month(config: Config, db: Database, current_date: date):
    """Show month"""
    from ..utils.files import get_monthly_file, read_file_lines, create_monthly_file

    file_path = get_monthly_file(config.data_dir, current_date.year, current_date.month)
    if not file_path.exists():
        create_monthly_file(config.data_dir, current_date.year, current_date.month)

    console.clear()
    lines = read_file_lines(file_path)
    for line in lines:
        console.print(line.rstrip())
    _pause()


def _cmd_future(config: Config, db: Database):
    """Show future log"""
    from ..utils.files import get_future_file, read_file_lines, create_future_file

    file_path = get_future_file(config.data_dir)
    if not file_path.exists():
        create_future_file(config.data_dir)

    console.clear()
    lines = read_file_lines(file_path)
    for line in lines:
        console.print(line.rstrip())
    _pause()


def _cmd_search(config: Config, db: Database, query: str):
    """Search"""
    if not query:
        console.print("Search: ", end="")
        try:
            query = input().strip()
        except (EOFError, KeyboardInterrupt):
            return

    if not query:
        return

    console.clear()
    results = db.search(query, 20)

    if not results:
        console.print(f"[dim]No results for '{query}'[/dim]")
        _pause()
        return

    console.print(f"\n[bold]Found {len(results)} result(s):[/bold]\n")

    for i, (entry, snippet) in enumerate(results, 1):
        source = entry.source_file
        if source.startswith("daily/"):
            source = source[6:-3]
        elif source.startswith("collections/"):
            source = source[12:-3]

        status = ""
        if entry.entry_type == "task":
            status_map = {"open": "[ ]", "complete": "[x]", "migrated": "[>]", "scheduled": "[<]", "cancelled": "[~]"}
            status = status_map.get(entry.status, "[ ]")
        elif entry.entry_type == "event":
            status = "○"
        elif entry.entry_type == "note":
            status = "-"

        console.print(f"[{i}] {source}: {status} {entry.content}")

    console.print("\n[dim][number] to view, [Enter] to return:[/dim] ", end="")
    try:
        choice = input().strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice:
        try:
            idx = int(choice)
            if 1 <= idx <= len(results):
                entry, _ = results[idx - 1]
                # Open in editor
                from .editor import open_in_editor
                file_path = config.data_dir / entry.source_file
                open_in_editor(config, file_path, entry.line_number)
        except ValueError:
            pass


def _cmd_sync(config: Config, db: Database, indexer: Indexer):
    """Sync"""
    from .sync import do_sync
    do_sync(config, db, indexer)
    _pause()


def _cmd_edit(config: Config, indexer: Indexer, current_date: date):
    """Edit today's file"""
    from .editor import open_in_editor
    file_path = create_daily_file(config.data_dir, current_date)
    open_in_editor(config, file_path)
    indexer.reindex_file(file_path)


def _cmd_undo(config: Config, db: Database, indexer: Indexer):
    """Undo last action"""
    from .undo import do_undo
    do_undo(config, db, indexer)
    _pause()


def _show_help():
    """Show help"""
    console.clear()
    console.print("""
[bold]CLIBuJo Interactive Mode[/bold]

Commands:
  a [t/e/n]  Add entry (task/event/note)
  x <num>    Complete task
  ~ <num>    Cancel task
  > <num>    Migrate task
  c          List collections
  m          View monthly log
  f          View future log
  /          Search
  s          Sync with git
  e          Edit in $EDITOR
  u          Undo last action
  d [date]   Change date
  q          Quit
  ?          This help

Quick add (type directly):
  [ ] task text    Add task
  * [ ] text       Priority task
  ○ event text     Add event
  - note text      Add note
""")
    _pause()


def _pause():
    """Wait for Enter"""
    try:
        input("[dim]Press Enter to continue...[/dim]")
    except (EOFError, KeyboardInterrupt):
        pass
