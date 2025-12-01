"""Data models for CLIBuJo"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class FileType(Enum):
    """Type of markdown file in the bujo"""
    DAILY = "daily"
    MONTHLY = "monthly"
    FUTURE = "future"
    COLLECTION = "collection"
    INDEX = "index"


class EntryType(Enum):
    """Type of bullet journal entry"""
    TASK = "task"
    EVENT = "event"
    NOTE = "note"


class TaskStatus(Enum):
    """Status of a task entry"""
    OPEN = "open"
    COMPLETE = "complete"
    MIGRATED = "migrated"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class Signifier(Enum):
    """Entry signifiers (priority markers)"""
    PRIORITY = "priority"
    INSPIRATION = "inspiration"
    EXPLORE = "explore"
    WAITING = "waiting"
    DELEGATED = "delegated"


@dataclass
class Context:
    """Context extracted from file path"""
    file_type: FileType
    file_path: str
    date: Optional[date] = None
    month: Optional[str] = None  # YYYY-MM format
    collection: Optional[str] = None
    collection_type: Optional[str] = None  # project, tracker, list


@dataclass
class Entry:
    """A parsed bullet journal entry"""
    entry_type: EntryType
    content: str
    raw_line: str
    line_number: int = 0
    status: Optional[TaskStatus] = None
    signifier: Optional[Signifier] = None
    migrated_to: Optional[str] = None
    migrated_from: Optional[str] = None
    entry_ref: Optional[str] = None

    def to_markdown(self) -> str:
        """Convert entry back to markdown format"""
        parts = []

        # Add signifier if present
        if self.signifier:
            sig_map = {
                Signifier.PRIORITY: "*",
                Signifier.INSPIRATION: "!",
                Signifier.EXPLORE: "?",
                Signifier.WAITING: "@",
                Signifier.DELEGATED: "#",
            }
            parts.append(sig_map.get(self.signifier, ""))

        # Add entry type marker
        if self.entry_type == EntryType.TASK:
            status_map = {
                TaskStatus.OPEN: "[ ]",
                TaskStatus.COMPLETE: "[x]",
                TaskStatus.MIGRATED: "[>]",
                TaskStatus.SCHEDULED: "[<]",
                TaskStatus.CANCELLED: "[~]",
            }
            parts.append(status_map.get(self.status, "[ ]"))
        elif self.entry_type == EntryType.EVENT:
            parts.append("○")
        elif self.entry_type == EntryType.NOTE:
            parts.append("-")

        # Add content
        parts.append(self.content)

        # Add migration hints
        if self.migrated_to:
            parts.append(f"→{self.migrated_to}")
        if self.migrated_from:
            parts.append(f"←{self.migrated_from}")

        return " ".join(parts)


@dataclass
class EntryRecord:
    """Entry as stored in SQLite"""
    id: int
    entry_ref: str
    source_file: str
    line_number: int
    raw_line: str
    entry_type: str
    status: Optional[str]
    signifier: Optional[str]
    content: str
    entry_date: Optional[date]
    created_at: datetime
    completed_at: Optional[datetime]
    collection: Optional[str]
    month: Optional[str]
    migrated_to: Optional[str]
    migrated_from: Optional[str]


@dataclass
class UndoAction:
    """Represents an undoable action"""
    action_type: str  # 'edit', 'add', 'delete'
    file_path: str
    line_number: int
    old_content: Optional[str]
    new_content: Optional[str]
    timestamp: datetime = field(default_factory=datetime.now)
