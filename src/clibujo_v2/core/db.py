"""Database initialization and connection management for CLIBuJo v2."""

import os
import sqlite3
from pathlib import Path
from typing import Optional

# Default data directory - respect BUJO_DIR env var
def get_data_dir() -> Path:
    """Get the data directory, creating if needed."""
    env_dir = os.environ.get("BUJO_DIR")
    if env_dir:
        data_dir = Path(env_dir)
    else:
        data_dir = Path.home() / ".local" / "share" / "bujo"

    data_dir.mkdir(parents=True, exist_ok=True)
    # Set restrictive permissions
    try:
        data_dir.chmod(0o700)
    except OSError:
        pass  # May fail on some filesystems
    return data_dir


def get_db_path() -> Path:
    """Get the database file path."""
    return get_data_dir() / "bujo.db"


SCHEMA = """
-- Configuration and metadata
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Collections (projects, trackers, lists)
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    type TEXT NOT NULL CHECK (type IN ('project', 'tracker', 'list')),
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    archived_at TEXT
);

-- Entries (tasks, events, notes)
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER,
    entry_date TEXT,
    entry_month TEXT,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('task', 'event', 'note')),
    status TEXT CHECK (status IN ('open', 'complete', 'migrated', 'scheduled', 'cancelled')),
    signifier TEXT CHECK (signifier IN ('priority', 'inspiration', 'explore', 'waiting', 'delegated')),
    content TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);

-- Entry migration history
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL,
    from_date TEXT,
    from_month TEXT,
    from_collection_id INTEGER,
    to_date TEXT,
    to_month TEXT,
    to_collection_id INTEGER,
    migrated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
    FOREIGN KEY (from_collection_id) REFERENCES collections(id),
    FOREIGN KEY (to_collection_id) REFERENCES collections(id)
);

-- Habits
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    frequency_type TEXT NOT NULL CHECK (frequency_type IN ('daily', 'weekly', 'monthly', 'specific_days')),
    frequency_target INTEGER DEFAULT 1,
    frequency_days TEXT,
    category TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'quit', 'completed')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Habit completions
CREATE TABLE IF NOT EXISTS habit_completions (
    id INTEGER PRIMARY KEY,
    habit_id INTEGER NOT NULL,
    completion_date TEXT NOT NULL,
    note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
    UNIQUE(habit_id, completion_date)
);

-- Undo history (50 levels max)
CREATE TABLE IF NOT EXISTS undo_history (
    id INTEGER PRIMARY KEY,
    action_type TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    old_data TEXT,
    new_data TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Sync metadata
CREATE TABLE IF NOT EXISTS sync_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Mood entries (one per day)
CREATE TABLE IF NOT EXISTS mood_entries (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    mood INTEGER CHECK (mood BETWEEN -5 AND 5),
    energy INTEGER CHECK (energy BETWEEN 1 AND 10),
    sleep_hours REAL CHECK (sleep_hours >= 0),
    sleep_quality INTEGER CHECK (sleep_quality BETWEEN 1 AND 5),
    irritability INTEGER CHECK (irritability BETWEEN 0 AND 5),
    anxiety INTEGER CHECK (anxiety BETWEEN 0 AND 5),
    racing_thoughts INTEGER CHECK (racing_thoughts BETWEEN 0 AND 5),
    impulsivity INTEGER CHECK (impulsivity BETWEEN 0 AND 5),
    concentration INTEGER CHECK (concentration BETWEEN 0 AND 5),
    social_drive INTEGER CHECK (social_drive BETWEEN -5 AND 5),
    appetite INTEGER CHECK (appetite BETWEEN -2 AND 2),
    note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Mood entry history for undo
CREATE TABLE IF NOT EXISTS mood_entry_history (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL,
    previous_data TEXT NOT NULL,
    changed_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entry_id) REFERENCES mood_entries(id) ON DELETE CASCADE
);

-- Watch/fitness data (one per day)
CREATE TABLE IF NOT EXISTS watch_data (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    steps INTEGER CHECK (steps >= 0),
    resting_hr INTEGER CHECK (resting_hr > 0),
    hrv INTEGER CHECK (hrv >= 0),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Medication definitions
CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    dosage TEXT,
    time_of_day TEXT CHECK (time_of_day IN ('morning', 'afternoon', 'evening', 'night')),
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    deactivated_at TEXT
);

-- Daily medication logs
CREATE TABLE IF NOT EXISTS med_logs (
    id INTEGER PRIMARY KEY,
    med_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    taken INTEGER DEFAULT 1,
    time_taken TEXT,
    note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (med_id) REFERENCES medications(id),
    UNIQUE(med_id, date)
);

-- Episode tracking (depression, hypomania, mania, mixed)
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    start_date TEXT NOT NULL,
    end_date TEXT,
    type TEXT NOT NULL CHECK (type IN ('depression', 'hypomania', 'mania', 'mixed')),
    severity INTEGER CHECK (severity BETWEEN 1 AND 5),
    note TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Custom trigger definitions for mood patterns
CREATE TABLE IF NOT EXISTS mood_triggers (
    id INTEGER PRIMARY KEY,
    condition TEXT NOT NULL,
    message TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Calculated baselines for mood metrics
CREATE TABLE IF NOT EXISTS baselines (
    metric TEXT PRIMARY KEY,
    value REAL NOT NULL,
    std_dev REAL NOT NULL,
    calculated_at TEXT NOT NULL,
    days_used INTEGER NOT NULL
);

-- Targets for mood metrics
CREATE TABLE IF NOT EXISTS targets (
    metric TEXT PRIMARY KEY,
    value REAL NOT NULL,
    set_at TEXT DEFAULT (datetime('now'))
);

-- Full-text search for entries
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    content,
    content=entries,
    content_rowid=id
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_entries_month ON entries(entry_month);
CREATE INDEX IF NOT EXISTS idx_entries_collection ON entries(collection_id);
CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status);
CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_habit_completions_date ON habit_completions(completion_date);
CREATE INDEX IF NOT EXISTS idx_habit_completions_habit ON habit_completions(habit_id);
CREATE INDEX IF NOT EXISTS idx_migrations_entry ON migrations(entry_id);
CREATE INDEX IF NOT EXISTS idx_undo_created ON undo_history(created_at);
CREATE INDEX IF NOT EXISTS idx_mood_entries_date ON mood_entries(date);
CREATE INDEX IF NOT EXISTS idx_watch_data_date ON watch_data(date);
CREATE INDEX IF NOT EXISTS idx_med_logs_date ON med_logs(date);
CREATE INDEX IF NOT EXISTS idx_episodes_dates ON episodes(start_date, end_date);
"""

# FTS triggers - each stored separately to avoid parsing issues
FTS_TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS entries_fts_insert AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
END
"""

FTS_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS entries_fts_delete AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, content) VALUES('delete', old.id, old.content);
END
"""

FTS_TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS entries_fts_update AFTER UPDATE OF content ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
END
"""

FTS_TRIGGERS = [FTS_TRIGGER_INSERT, FTS_TRIGGER_DELETE, FTS_TRIGGER_UPDATE]


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a database connection with proper settings."""
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize the database with schema."""
    if db_path is None:
        db_path = get_db_path()

    conn = get_connection(db_path)

    # Create main schema
    conn.executescript(SCHEMA)

    # Create FTS triggers (separate to avoid parsing issues)
    for trigger_sql in FTS_TRIGGERS:
        trigger_sql = trigger_sql.strip()
        if trigger_sql:
            try:
                conn.execute(trigger_sql)
            except sqlite3.OperationalError:
                pass  # Trigger may already exist

    conn.commit()
    conn.close()

    # Set restrictive permissions on database file
    try:
        db_path.chmod(0o600)
    except OSError:
        pass


def db_exists(db_path: Optional[Path] = None) -> bool:
    """Check if database exists."""
    if db_path is None:
        db_path = get_db_path()
    return db_path.exists()


def ensure_db() -> None:
    """Ensure database exists and is initialized."""
    if not db_exists():
        init_db()


def cleanup_undo_history(conn: sqlite3.Connection, max_entries: int = 50) -> None:
    """Keep only the most recent undo entries."""
    conn.execute("""
        DELETE FROM undo_history
        WHERE id NOT IN (
            SELECT id FROM undo_history
            ORDER BY created_at DESC
            LIMIT ?
        )
    """, (max_entries,))
    conn.commit()
