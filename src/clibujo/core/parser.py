"""Markdown parser for CLIBuJo entries"""

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Optional

from .models import Context, Entry, EntryType, FileType, Signifier, TaskStatus


# Default signifier mapping
DEFAULT_SIGNIFIERS = {
    "*": Signifier.PRIORITY,
    "!": Signifier.INSPIRATION,
    "?": Signifier.EXPLORE,
    "@": Signifier.WAITING,
    "#": Signifier.DELEGATED,
}

# Task status mapping
STATUS_MAP = {
    " ": TaskStatus.OPEN,
    "x": TaskStatus.COMPLETE,
    ">": TaskStatus.MIGRATED,
    "<": TaskStatus.SCHEDULED,
    "~": TaskStatus.CANCELLED,
}

# Reverse status mapping for output
STATUS_CHAR_MAP = {v: k for k, v in STATUS_MAP.items()}


def build_signifier_pattern(signifiers: dict[str, str]) -> re.Pattern:
    """Build regex pattern for signifiers from config"""
    # Escape special regex characters
    chars = "".join(re.escape(c) for c in signifiers.keys())
    if chars:
        return re.compile(rf"^([{chars}])\s+")
    return re.compile(r"^$")  # Never matches


def get_signifier_from_char(char: str, signifiers: dict[str, str]) -> Optional[Signifier]:
    """Convert signifier character to Signifier enum"""
    name = signifiers.get(char)
    if name:
        try:
            return Signifier(name)
        except ValueError:
            return None
    return DEFAULT_SIGNIFIERS.get(char)


# Compiled regex patterns
TASK_PATTERN = re.compile(r"^\[([ x><~])\]\s+(.+)")
EVENT_PATTERN = re.compile(r"^○\s*(.+)")
NOTE_PATTERN = re.compile(r"^-\s+(.+)")
MIGRATION_TO_PATTERN = re.compile(r"\s*→(\S+)\s*$")
MIGRATION_FROM_PATTERN = re.compile(r"\s*←(\S+)\s*$")

# Date patterns for file parsing
DAILY_FILE_PATTERN = re.compile(r"(\d{4})-(\d{2})-(\d{2})\.md$")
MONTHLY_FILE_PATTERN = re.compile(r"(\d{4})-(\d{2})\.md$")


def generate_entry_ref(source_file: str, content: str, entry_date: Optional[str] = None) -> str:
    """Generate a stable 6-char reference for an entry"""
    data = f"{source_file}:{content}:{entry_date or ''}"
    return hashlib.sha256(data.encode()).hexdigest()[:6]


def parse_entry(
    line: str,
    line_number: int = 0,
    signifiers: Optional[dict[str, str]] = None,
) -> Optional[Entry]:
    """Parse a single line into an Entry object"""
    if signifiers is None:
        signifiers = {"*": "priority", "!": "inspiration", "?": "explore"}

    raw_line = line
    line = line.strip()

    # Skip empty lines and headers
    if not line or line.startswith("#"):
        return None

    # Check for signifier prefix
    signifier = None
    signifier_pattern = build_signifier_pattern(signifiers)
    signifier_match = signifier_pattern.match(line)
    if signifier_match:
        sig_char = signifier_match.group(1)
        signifier = get_signifier_from_char(sig_char, signifiers)
        line = line[signifier_match.end():]

    # Check for migration hints and extract them
    migrated_to = None
    migrated_from = None

    to_match = MIGRATION_TO_PATTERN.search(line)
    if to_match:
        migrated_to = to_match.group(1)
        line = line[: to_match.start()].strip()

    from_match = MIGRATION_FROM_PATTERN.search(line)
    if from_match:
        migrated_from = from_match.group(1)
        line = line[: from_match.start()].strip()

    # Parse entry type
    task_match = TASK_PATTERN.match(line)
    if task_match:
        status_char = task_match.group(1)
        status = STATUS_MAP.get(status_char, TaskStatus.OPEN)
        return Entry(
            entry_type=EntryType.TASK,
            content=task_match.group(2).strip(),
            raw_line=raw_line,
            line_number=line_number,
            status=status,
            signifier=signifier,
            migrated_to=migrated_to,
            migrated_from=migrated_from,
        )

    event_match = EVENT_PATTERN.match(line)
    if event_match:
        return Entry(
            entry_type=EntryType.EVENT,
            content=event_match.group(1).strip(),
            raw_line=raw_line,
            line_number=line_number,
            signifier=signifier,
        )

    note_match = NOTE_PATTERN.match(line)
    if note_match:
        return Entry(
            entry_type=EntryType.NOTE,
            content=note_match.group(1).strip(),
            raw_line=raw_line,
            line_number=line_number,
            signifier=signifier,
        )

    return None  # Not a recognized entry


def parse_file(
    file_path: Path,
    signifiers: Optional[dict[str, str]] = None,
) -> list[Entry]:
    """Parse all entries from a markdown file"""
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8")
    entries = []

    for line_num, line in enumerate(content.splitlines(), 1):
        entry = parse_entry(line, line_num, signifiers)
        if entry:
            entries.append(entry)

    return entries


def determine_context(file_path: Path, data_dir: Path) -> Context:
    """Determine context from file path"""
    # Get relative path from data directory
    try:
        rel_path = file_path.relative_to(data_dir)
    except ValueError:
        rel_path = file_path

    rel_str = str(rel_path)
    file_name = file_path.name

    # Check for daily log
    if rel_str.startswith("daily/") or rel_str.startswith("daily\\"):
        match = DAILY_FILE_PATTERN.search(file_name)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return Context(
                file_type=FileType.DAILY,
                file_path=rel_str,
                date=date(year, month, day),
                month=f"{year:04d}-{month:02d}",
            )

    # Check for monthly log
    if rel_str.startswith("months/") or rel_str.startswith("months\\"):
        match = MONTHLY_FILE_PATTERN.search(file_name)
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            return Context(
                file_type=FileType.MONTHLY,
                file_path=rel_str,
                month=f"{year:04d}-{month:02d}",
            )

    # Check for future log
    if file_name == "future.md":
        return Context(
            file_type=FileType.FUTURE,
            file_path=rel_str,
        )

    # Check for index
    if file_name == "index.md":
        return Context(
            file_type=FileType.INDEX,
            file_path=rel_str,
        )

    # Check for collections
    if rel_str.startswith("collections/") or rel_str.startswith("collections\\"):
        parts = rel_path.parts
        if len(parts) >= 3:
            collection_type = parts[1]
            collection_name = file_path.stem
            return Context(
                file_type=FileType.COLLECTION,
                file_path=rel_str,
                collection=f"{collection_type}/{collection_name}",
                collection_type=collection_type,
            )
        elif len(parts) >= 2:
            collection_name = file_path.stem
            return Context(
                file_type=FileType.COLLECTION,
                file_path=rel_str,
                collection=collection_name,
            )

    # Default to collection
    return Context(
        file_type=FileType.COLLECTION,
        file_path=rel_str,
    )


def entry_to_markdown(entry: Entry) -> str:
    """Convert Entry back to markdown line"""
    parts = []

    # Add signifier if present
    if entry.signifier:
        sig_map = {
            Signifier.PRIORITY: "*",
            Signifier.INSPIRATION: "!",
            Signifier.EXPLORE: "?",
            Signifier.WAITING: "@",
            Signifier.DELEGATED: "#",
        }
        sig_char = sig_map.get(entry.signifier)
        if sig_char:
            parts.append(sig_char)

    # Add entry type marker
    if entry.entry_type == EntryType.TASK:
        status_char = STATUS_CHAR_MAP.get(entry.status, " ")
        parts.append(f"[{status_char}]")
    elif entry.entry_type == EntryType.EVENT:
        parts.append("○")
    elif entry.entry_type == EntryType.NOTE:
        parts.append("-")

    # Add content
    parts.append(entry.content)

    # Add migration hints
    if entry.migrated_to:
        parts.append(f"→{entry.migrated_to}")
    if entry.migrated_from:
        parts.append(f"←{entry.migrated_from}")

    return " ".join(parts)


def update_task_status(line: str, new_status: TaskStatus) -> str:
    """Update task status in a line, preserving everything else"""
    # Find the task marker
    task_match = re.search(r"\[([ x><~])\]", line)
    if not task_match:
        return line

    new_char = STATUS_CHAR_MAP.get(new_status, " ")
    return line[: task_match.start() + 1] + new_char + line[task_match.end() - 1 :]


def add_migration_hint(line: str, destination: str) -> str:
    """Add migration destination hint to a line"""
    line = line.rstrip()
    # Remove existing migration hint if present
    line = MIGRATION_TO_PATTERN.sub("", line).rstrip()
    return f"{line} →{destination}"


def create_migrated_entry(content: str, source: str, signifier: Optional[Signifier] = None) -> str:
    """Create a new task entry with migration source hint"""
    parts = []

    if signifier:
        sig_map = {
            Signifier.PRIORITY: "*",
            Signifier.INSPIRATION: "!",
            Signifier.EXPLORE: "?",
            Signifier.WAITING: "@",
            Signifier.DELEGATED: "#",
        }
        sig_char = sig_map.get(signifier)
        if sig_char:
            parts.append(sig_char)

    parts.append("[ ]")
    parts.append(content)
    parts.append(f"←{source}")

    return " ".join(parts)
