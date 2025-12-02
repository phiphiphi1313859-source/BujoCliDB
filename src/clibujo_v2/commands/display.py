"""Display formatting utilities for CLIBuJo v2."""

from datetime import date, datetime
from typing import List, Optional

from ..core.models import (
    Entry,
    Collection,
    Habit,
    SIGNIFIER_SYMBOLS,
    STATUS_SYMBOLS,
    ENTRY_TYPE_SYMBOLS,
)


def format_entry(entry: Entry, show_id: bool = True) -> str:
    """Format an entry for display.

    Args:
        entry: Entry to format
        show_id: Whether to show entry ID prefix

    Returns:
        Formatted string
    """
    parts = []

    # ID prefix
    if show_id:
        parts.append(f"[{entry.id}]")

    # Signifier
    if entry.signifier:
        symbol = SIGNIFIER_SYMBOLS.get(entry.signifier, "")
        if symbol:
            parts.append(symbol)

    # Type/status indicator
    if entry.entry_type == "task":
        symbol = STATUS_SYMBOLS.get(entry.status, "[ ]")
        parts.append(symbol)
    else:
        symbol = ENTRY_TYPE_SYMBOLS.get(entry.entry_type, "-")
        parts.append(symbol)

    # Content
    parts.append(entry.content)

    return " ".join(parts)


def format_entry_list(
    entries: List[Entry],
    title: Optional[str] = None,
    show_ids: bool = True,
) -> str:
    """Format a list of entries.

    Args:
        entries: List of entries
        title: Optional section title
        show_ids: Whether to show entry IDs

    Returns:
        Formatted string with newlines
    """
    lines = []

    if title:
        lines.append(f"== {title} ==")
        lines.append("")

    if not entries:
        lines.append("  (no entries)")
    else:
        for entry in entries:
            lines.append(f"  {format_entry(entry, show_ids)}")

    return "\n".join(lines)


def format_date_header(entry_date: str) -> str:
    """Format a date as a header."""
    try:
        dt = datetime.strptime(entry_date, "%Y-%m-%d")
        day_name = dt.strftime("%A")
        formatted = dt.strftime("%B %d, %Y")
        return f"{day_name}, {formatted}"
    except ValueError:
        return entry_date


def format_month_header(entry_month: str) -> str:
    """Format a month as a header."""
    try:
        dt = datetime.strptime(entry_month + "-01", "%Y-%m-%d")
        return dt.strftime("%B %Y")
    except ValueError:
        return entry_month


def format_daily_log(
    entry_date: str,
    entries: List[Entry],
    habits: Optional[List[dict]] = None,
) -> str:
    """Format a complete daily log view.

    Args:
        entry_date: Date string (YYYY-MM-DD)
        entries: List of entries for the day
        habits: Optional list of habit dicts with 'habit' and 'completed' keys

    Returns:
        Formatted daily log
    """
    lines = []

    # Header
    header = format_date_header(entry_date)
    lines.append("=" * len(header))
    lines.append(header)
    lines.append("=" * len(header))
    lines.append("")

    # Group entries by type
    tasks = [e for e in entries if e.entry_type == "task"]
    events = [e for e in entries if e.entry_type == "event"]
    notes = [e for e in entries if e.entry_type == "note"]

    # Events first (schedule for the day)
    if events:
        lines.append("EVENTS")
        for entry in events:
            lines.append(f"  {format_entry(entry)}")
        lines.append("")

    # Tasks
    if tasks:
        lines.append("TASKS")
        for entry in tasks:
            lines.append(f"  {format_entry(entry)}")
        lines.append("")

    # Notes
    if notes:
        lines.append("NOTES")
        for entry in notes:
            lines.append(f"  {format_entry(entry)}")
        lines.append("")

    # Habits at the bottom
    if habits:
        lines.append("HABITS")
        for h in habits:
            habit = h["habit"]
            completed = h["completed"]
            status = "[x]" if completed else "[ ]"
            freq = habit.get_frequency_display()
            lines.append(f"  {status} {habit.name} ({freq})")
        lines.append("")

    return "\n".join(lines)


def format_collection(
    collection: Collection,
    entries: List[Entry],
    stats: Optional[dict] = None,
) -> str:
    """Format a collection view."""
    lines = []

    # Header
    type_label = collection.type.upper()
    header = f"{type_label}: {collection.name}"
    lines.append("=" * len(header))
    lines.append(header)
    lines.append("=" * len(header))

    if collection.description:
        lines.append(collection.description)
    lines.append("")

    # Stats
    if stats:
        if collection.type == "project":
            open_count = stats.get("open", 0)
            complete_count = stats.get("complete", 0)
            total = open_count + complete_count
            if total > 0:
                pct = int((complete_count / total) * 100)
                lines.append(f"Progress: {complete_count}/{total} tasks ({pct}%)")
                lines.append("")

    # Entries
    if not entries:
        lines.append("  (no entries)")
    else:
        for entry in entries:
            lines.append(f"  {format_entry(entry)}")

    lines.append("")
    return "\n".join(lines)


def format_habit_status(habit: Habit, progress: dict, completed_today: bool) -> str:
    """Format a habit's status for display."""
    status_indicator = "[x]" if completed_today else "[ ]"
    freq = habit.get_frequency_display()

    progress_bar = ""
    if progress["target"] > 1:
        filled = min(progress["completed"], progress["target"])
        empty = progress["target"] - filled
        progress_bar = f" [{'#' * filled}{'.' * empty}]"

    streak = ""
    if progress["streak"] > 0:
        streak = f" ({progress['streak']} streak)"

    return f"{status_indicator} {habit.name} ({freq}){progress_bar}{streak}"


def format_habits_list(
    habits: List[Habit],
    progress_map: dict,
    completed_map: dict,
) -> str:
    """Format a list of habits with their status.

    Args:
        habits: List of habits
        progress_map: Dict mapping habit.id to progress dict
        completed_map: Dict mapping habit.id to bool (completed today)

    Returns:
        Formatted string
    """
    lines = []
    lines.append("== HABITS ==")
    lines.append("")

    if not habits:
        lines.append("  (no habits)")
        return "\n".join(lines)

    # Group by category
    by_category = {}
    for habit in habits:
        cat = habit.category or "Uncategorized"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(habit)

    for category in sorted(by_category.keys()):
        if len(by_category) > 1:
            lines.append(f"  [{category}]")

        for habit in by_category[category]:
            progress = progress_map.get(habit.id, {"completed": 0, "target": 1, "streak": 0})
            completed = completed_map.get(habit.id, False)
            line = format_habit_status(habit, progress, completed)
            lines.append(f"    {line}" if len(by_category) > 1 else f"  {line}")

        lines.append("")

    return "\n".join(lines)


def format_search_results(entries: List[Entry], query: str) -> str:
    """Format search results."""
    lines = []
    lines.append(f"== Search: '{query}' ({len(entries)} results) ==")
    lines.append("")

    for entry in entries:
        # Show context (date/collection)
        context = ""
        if entry.entry_date:
            context = entry.entry_date
        elif entry.entry_month:
            context = f"{entry.entry_month} (monthly)"
        elif entry.collection_id:
            context = f"collection #{entry.collection_id}"

        lines.append(f"  {format_entry(entry)}  [{context}]")

    if not entries:
        lines.append("  (no results)")

    return "\n".join(lines)


def format_undo_preview(descriptions: List[str]) -> str:
    """Format undo history preview."""
    lines = []
    lines.append("== Recent Actions (newest first) ==")
    lines.append("")

    for i, desc in enumerate(descriptions, 1):
        lines.append(f"  {i}. {desc}")

    if not descriptions:
        lines.append("  (no actions to undo)")

    return "\n".join(lines)
