"""Data models for CLIBuJo v2."""

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class EntryType(Enum):
    """Type of bullet journal entry."""
    TASK = "task"
    EVENT = "event"
    NOTE = "note"


class TaskStatus(Enum):
    """Status of a task entry."""
    OPEN = "open"
    COMPLETE = "complete"
    MIGRATED = "migrated"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class Signifier(Enum):
    """Entry signifiers (priority markers)."""
    PRIORITY = "priority"
    INSPIRATION = "inspiration"
    EXPLORE = "explore"
    WAITING = "waiting"
    DELEGATED = "delegated"


class CollectionType(Enum):
    """Type of collection."""
    PROJECT = "project"
    TRACKER = "tracker"
    LIST = "list"


class HabitStatus(Enum):
    """Habit lifecycle status."""
    ACTIVE = "active"
    PAUSED = "paused"
    QUIT = "quit"
    COMPLETED = "completed"


class FrequencyType(Enum):
    """Types of habit frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SPECIFIC_DAYS = "specific_days"


@dataclass
class Entry:
    """A bullet journal entry."""
    id: Optional[int] = None
    collection_id: Optional[int] = None
    entry_date: Optional[str] = None  # YYYY-MM-DD for daily entries
    entry_month: Optional[str] = None  # YYYY-MM for monthly/future entries
    entry_type: str = "task"
    status: Optional[str] = "open"  # Only for tasks
    signifier: Optional[str] = None
    content: str = ""
    sort_order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Entry":
        """Create Entry from database row."""
        return cls(**dict(row))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Entry":
        """Create from JSON string."""
        return cls(**json.loads(json_str))


@dataclass
class Collection:
    """A collection (project, tracker, or list)."""
    id: Optional[int] = None
    name: str = ""
    type: str = "project"
    description: Optional[str] = None
    created_at: Optional[str] = None
    archived_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Collection":
        """Create Collection from database row."""
        return cls(**dict(row))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @property
    def is_archived(self) -> bool:
        """Check if collection is archived."""
        return self.archived_at is not None


@dataclass
class Migration:
    """Record of a task migration."""
    id: Optional[int] = None
    entry_id: int = 0
    from_date: Optional[str] = None
    from_month: Optional[str] = None
    from_collection_id: Optional[int] = None
    to_date: Optional[str] = None
    to_month: Optional[str] = None
    to_collection_id: Optional[int] = None
    migrated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Migration":
        """Create Migration from database row."""
        return cls(**dict(row))


@dataclass
class Habit:
    """A habit to track."""
    id: Optional[int] = None
    name: str = ""
    frequency_type: str = "daily"
    frequency_target: int = 1
    frequency_days: Optional[str] = None  # Comma-separated: "mon,wed,fri"
    category: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Habit":
        """Create Habit from database row."""
        return cls(**dict(row))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Habit":
        """Create from JSON string."""
        return cls(**json.loads(json_str))

    @property
    def frequency_days_list(self) -> List[str]:
        """Get frequency days as list."""
        if self.frequency_days:
            return [d.strip().lower() for d in self.frequency_days.split(",")]
        return []

    def get_frequency_display(self) -> str:
        """Get human-readable frequency."""
        if self.frequency_type == "daily":
            return "daily"
        elif self.frequency_type == "weekly":
            if self.frequency_target == 1:
                return "weekly"
            return f"weekly:{self.frequency_target}"
        elif self.frequency_type == "monthly":
            if self.frequency_target == 1:
                return "monthly"
            return f"monthly:{self.frequency_target}"
        elif self.frequency_type == "specific_days":
            return f"days:{self.frequency_days}"
        return self.frequency_type


@dataclass
class HabitCompletion:
    """A habit completion record."""
    id: Optional[int] = None
    habit_id: int = 0
    completion_date: str = ""  # YYYY-MM-DD
    note: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "HabitCompletion":
        """Create HabitCompletion from database row."""
        return cls(**dict(row))


@dataclass
class UndoAction:
    """An undoable action record."""
    id: Optional[int] = None
    action_type: str = ""  # 'create', 'update', 'delete'
    table_name: str = ""
    record_id: int = 0
    old_data: Optional[str] = None  # JSON
    new_data: Optional[str] = None  # JSON
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "UndoAction":
        """Create UndoAction from database row."""
        return cls(**dict(row))


# Signifier symbols for display
SIGNIFIER_SYMBOLS = {
    "priority": "*",
    "inspiration": "!",
    "explore": "?",
    "waiting": "@",
    "delegated": "#",
}

SIGNIFIER_FROM_SYMBOL = {v: k for k, v in SIGNIFIER_SYMBOLS.items()}

# Task status symbols for display
STATUS_SYMBOLS = {
    "open": "[ ]",
    "complete": "[x]",
    "migrated": "[>]",
    "scheduled": "[<]",
    "cancelled": "[~]",
}

STATUS_FROM_SYMBOL = {v: k for k, v in STATUS_SYMBOLS.items()}

# Entry type symbols
ENTRY_TYPE_SYMBOLS = {
    "task": "[ ]",
    "event": "○",
    "note": "-",
}
