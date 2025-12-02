"""Migration tool to import data from CLIBuJo v1 (markdown format).

This tool parses the markdown files from v1 and imports them into the v2 SQLite database.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from ..core.db import ensure_db, get_connection
from ..core.entries import create_entry
from ..core.collections import create_collection, get_collection_by_name
from ..core.habits import create_habit, record_completion


# Regex patterns for parsing v1 markdown
TASK_PATTERN = re.compile(r"^(\*?!?\??\@?\#?)\s*\[([ x>~<])\]\s*(.+)$")
EVENT_PATTERN = re.compile(r"^(\*?!?\??\@?\#?)\s*(○|o)\s*(.+)$")
NOTE_PATTERN = re.compile(r"^(\*?!?\??\@?\#?)\s*-\s*(.+)$")

# Signifier mapping
SIGNIFIER_MAP = {
    "*": "priority",
    "!": "inspiration",
    "?": "explore",
    "@": "waiting",
    "#": "delegated",
}

# Status mapping
STATUS_MAP = {
    " ": "open",
    "x": "complete",
    ">": "migrated",
    "<": "scheduled",
    "~": "cancelled",
}


def parse_signifier(prefix: str) -> Optional[str]:
    """Parse signifier from prefix characters."""
    for char, signifier in SIGNIFIER_MAP.items():
        if char in prefix:
            return signifier
    return None


def parse_entry_line(line: str) -> Optional[Dict]:
    """Parse a single entry line.

    Returns dict with: type, status, signifier, content
    """
    line = line.strip()
    if not line:
        return None

    # Try task pattern
    match = TASK_PATTERN.match(line)
    if match:
        prefix, status_char, content = match.groups()
        return {
            "type": "task",
            "status": STATUS_MAP.get(status_char, "open"),
            "signifier": parse_signifier(prefix),
            "content": content.strip(),
        }

    # Try event pattern
    match = EVENT_PATTERN.match(line)
    if match:
        prefix, _, content = match.groups()
        return {
            "type": "event",
            "status": None,
            "signifier": parse_signifier(prefix),
            "content": content.strip(),
        }

    # Try note pattern
    match = NOTE_PATTERN.match(line)
    if match:
        prefix, content = match.groups()
        return {
            "type": "note",
            "status": None,
            "signifier": parse_signifier(prefix),
            "content": content.strip(),
        }

    return None


def parse_daily_log(filepath: Path) -> Tuple[str, List[Dict]]:
    """Parse a daily log file.

    Returns (date_string, list of entry dicts).
    """
    # Extract date from filename (expected: YYYY-MM-DD.md)
    date_str = filepath.stem

    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            entry = parse_entry_line(line)
            if entry:
                entries.append(entry)

    return date_str, entries


def parse_collection_file(filepath: Path) -> Tuple[str, str, Optional[str], List[Dict]]:
    """Parse a collection file.

    Returns (name, type, description, entries).
    """
    name = filepath.stem
    coll_type = "project"  # Default

    # Determine type from parent directory name if available
    parent_name = filepath.parent.name.lower()
    if "tracker" in parent_name:
        coll_type = "tracker"
    elif "list" in parent_name:
        coll_type = "list"

    description = None
    entries = []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # First non-entry lines might be description
    desc_lines = []
    for line in lines:
        entry = parse_entry_line(line)
        if entry:
            entries.append(entry)
        elif line.strip() and not line.startswith("#"):
            if not entries:  # Still in description area
                desc_lines.append(line.strip())

    if desc_lines:
        description = " ".join(desc_lines)

    return name, coll_type, description, entries


def parse_habits_file(filepath: Path) -> List[Dict]:
    """Parse habits tracking file.

    Expected format (from v1):
    ```
    ## Habits
    - [x] Exercise (daily)
    - [ ] Read (daily)
    - [x] Meditate (days:mon,wed,fri)
    ```

    Returns list of habit dicts.
    """
    habits = []
    habit_pattern = re.compile(r"^\s*-\s*\[([ x])\]\s*(.+?)(?:\s*\(([^)]+)\))?\s*$")

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            match = habit_pattern.match(line)
            if match:
                completed, name, frequency = match.groups()
                habits.append({
                    "name": name.strip(),
                    "frequency": frequency or "daily",
                    "completed_today": completed == "x",
                })

    return habits


def find_v1_data_dir() -> Optional[Path]:
    """Try to find the v1 data directory."""
    possible_paths = [
        Path.home() / ".local" / "share" / "bujo",
        Path.home() / ".bujo",
        Path.home() / "bujo",
    ]

    for path in possible_paths:
        if path.exists() and (path / "daily").exists():
            return path

    return None


def migrate_from_v1(
    v1_dir: Path,
    dry_run: bool = False,
) -> Dict:
    """Migrate data from v1 directory.

    Args:
        v1_dir: Path to v1 data directory
        dry_run: If True, don't actually import, just count

    Returns:
        Statistics dict with counts
    """
    ensure_db()

    stats = {
        "daily_logs": 0,
        "entries": 0,
        "collections": 0,
        "collection_entries": 0,
        "habits": 0,
        "errors": [],
    }

    conn = get_connection() if not dry_run else None

    try:
        # Import daily logs
        daily_dir = v1_dir / "daily"
        if daily_dir.exists():
            for md_file in daily_dir.glob("*.md"):
                try:
                    date_str, entries = parse_daily_log(md_file)
                    stats["daily_logs"] += 1

                    for entry_data in entries:
                        if not dry_run:
                            create_entry(
                                content=entry_data["content"],
                                entry_type=entry_data["type"],
                                entry_date=date_str,
                                status=entry_data["status"],
                                signifier=entry_data["signifier"],
                                conn=conn,
                            )
                        stats["entries"] += 1

                except Exception as e:
                    stats["errors"].append(f"Daily {md_file.name}: {e}")

        # Import monthly logs
        monthly_dir = v1_dir / "monthly"
        if monthly_dir.exists():
            for md_file in monthly_dir.glob("*.md"):
                try:
                    # Month files named YYYY-MM.md
                    month_str = md_file.stem

                    with open(md_file, "r", encoding="utf-8") as f:
                        for line in f:
                            entry = parse_entry_line(line)
                            if entry:
                                if not dry_run:
                                    create_entry(
                                        content=entry["content"],
                                        entry_type=entry["type"],
                                        entry_month=month_str,
                                        status=entry["status"],
                                        signifier=entry["signifier"],
                                        conn=conn,
                                    )
                                stats["entries"] += 1

                except Exception as e:
                    stats["errors"].append(f"Monthly {md_file.name}: {e}")

        # Import collections
        collections_dir = v1_dir / "collections"
        if collections_dir.exists():
            for md_file in collections_dir.glob("**/*.md"):
                try:
                    name, coll_type, description, entries = parse_collection_file(md_file)

                    if not dry_run:
                        # Check if collection exists
                        existing = get_collection_by_name(name)
                        if existing:
                            coll_id = existing.id
                        else:
                            coll = create_collection(name, coll_type, description, conn=conn)
                            coll_id = coll.id
                            stats["collections"] += 1

                        for entry_data in entries:
                            create_entry(
                                content=entry_data["content"],
                                entry_type=entry_data["type"],
                                collection_id=coll_id,
                                status=entry_data["status"],
                                signifier=entry_data["signifier"],
                                conn=conn,
                            )
                            stats["collection_entries"] += 1
                    else:
                        stats["collections"] += 1
                        stats["collection_entries"] += len(entries)

                except Exception as e:
                    stats["errors"].append(f"Collection {md_file.name}: {e}")

        # Import habits
        habits_file = v1_dir / "habits.md"
        if habits_file.exists():
            try:
                habits = parse_habits_file(habits_file)
                today = datetime.now().strftime("%Y-%m-%d")

                for habit_data in habits:
                    if not dry_run:
                        try:
                            habit = create_habit(
                                name=habit_data["name"],
                                frequency=habit_data["frequency"],
                                conn=conn,
                            )
                            stats["habits"] += 1

                            if habit_data["completed_today"]:
                                record_completion(habit.id, today, conn=conn)
                        except Exception:
                            # Habit might already exist
                            pass
                    else:
                        stats["habits"] += 1

            except Exception as e:
                stats["errors"].append(f"Habits: {e}")

        if conn:
            conn.commit()

    finally:
        if conn:
            conn.close()

    return stats


def migrate_from_path(path: str, dry_run: bool = False) -> Dict:
    """Migrate from a specific path."""
    v1_dir = Path(path)
    if not v1_dir.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    return migrate_from_v1(v1_dir, dry_run)
