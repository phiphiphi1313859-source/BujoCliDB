# CLIBuJo v2: SQLite-First Rewrite Plan

## Overview

Complete rewrite of CLIBuJo to use SQLite as the source of truth instead of markdown files. This enables:
- Simpler architecture (no parser/indexer)
- Atomic operations
- Better undo/migration tracking
- Unified sync strategy with cliMood
- Future mood tracker integration

## Database Schema

```sql
-- Configuration and metadata
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Collections (projects, trackers, lists, logs)
CREATE TABLE collections (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    type TEXT NOT NULL CHECK (type IN ('project', 'tracker', 'list', 'daily', 'monthly', 'future')),
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    archived_at TEXT
);

-- Entries (tasks, events, notes)
CREATE TABLE entries (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER,                      -- NULL for daily/future log entries
    entry_date TEXT,                            -- YYYY-MM-DD for daily entries
    entry_month TEXT,                           -- YYYY-MM for monthly/future entries
    entry_type TEXT NOT NULL CHECK (entry_type IN ('task', 'event', 'note')),
    status TEXT CHECK (status IN ('open', 'complete', 'migrated', 'scheduled', 'cancelled')),
    signifier TEXT CHECK (signifier IN ('priority', 'inspiration', 'explore', 'waiting', 'delegated')),
    content TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,               -- For manual ordering within a day/collection
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);

-- Entry migration history
CREATE TABLE migrations (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL,
    from_date TEXT,                             -- Source daily log date
    from_month TEXT,                            -- Source month
    from_collection_id INTEGER,                 -- Source collection
    to_date TEXT,                               -- Destination daily log date
    to_month TEXT,                              -- Destination month (future log)
    to_collection_id INTEGER,                   -- Destination collection
    migrated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entry_id) REFERENCES entries(id),
    FOREIGN KEY (from_collection_id) REFERENCES collections(id),
    FOREIGN KEY (to_collection_id) REFERENCES collections(id)
);

-- Habits
CREATE TABLE habits (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    frequency_type TEXT NOT NULL CHECK (frequency_type IN ('daily', 'weekly', 'monthly', 'specific_days')),
    frequency_target INTEGER DEFAULT 1,         -- Times per period
    frequency_days TEXT,                        -- Comma-separated days for specific_days (mon,wed,fri)
    category TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'quit', 'completed')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Habit completions
CREATE TABLE habit_completions (
    id INTEGER PRIMARY KEY,
    habit_id INTEGER NOT NULL,
    completion_date TEXT NOT NULL,              -- YYYY-MM-DD
    note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (habit_id) REFERENCES habits(id),
    UNIQUE(habit_id, completion_date)
);

-- Undo history (multi-level)
CREATE TABLE undo_history (
    id INTEGER PRIMARY KEY,
    action_type TEXT NOT NULL,                  -- 'entry_create', 'entry_update', 'entry_delete', etc.
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    old_data TEXT,                              -- JSON snapshot of old state
    new_data TEXT,                              -- JSON snapshot of new state
    created_at TEXT DEFAULT (datetime('now'))
);

-- Sync metadata
CREATE TABLE sync_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Full-text search
CREATE VIRTUAL TABLE entries_fts USING fts5(
    content,
    content=entries,
    content_rowid=id
);

-- Triggers for FTS sync
CREATE TRIGGER entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER entries_au AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
END;

-- Indexes
CREATE INDEX idx_entries_date ON entries(entry_date);
CREATE INDEX idx_entries_month ON entries(entry_month);
CREATE INDEX idx_entries_collection ON entries(collection_id);
CREATE INDEX idx_entries_status ON entries(status);
CREATE INDEX idx_habit_completions_date ON habit_completions(completion_date);
CREATE INDEX idx_habit_completions_habit ON habit_completions(habit_id);
CREATE INDEX idx_migrations_entry ON migrations(entry_id);
```

## File Structure

```
~/.local/share/bujo/
├── bujo.db                 # Main SQLite database
├── config.toml             # Configuration file
├── exports/                # Generated PDFs
│   └── bujo_2025-12-02.pdf
└── .sync_lock              # Sync lock file
```

## Module Structure

```
src/clibujo/
├── __init__.py
├── cli.py                  # Main CLI entry point
├── core/
│   ├── __init__.py
│   ├── db.py               # Database init, connection, schema
│   ├── models.py           # Dataclasses for Entry, Habit, Collection, etc.
│   ├── entries.py          # Entry CRUD operations
│   ├── collections.py      # Collection operations
│   ├── habits.py           # Habit tracking operations
│   ├── migrations.py       # Task migration operations
│   ├── undo.py             # Undo system
│   └── config.py           # Configuration management
├── commands/
│   ├── __init__.py
│   ├── add.py              # Add entries
│   ├── view.py             # View daily/weekly/monthly
│   ├── complete.py         # Complete/cancel tasks
│   ├── migrate.py          # Migrate/schedule tasks
│   ├── collection.py       # Collection management
│   ├── habit.py            # Habit commands
│   ├── search.py           # Search functionality
│   ├── stats.py            # Statistics
│   ├── export.py           # PDF export
│   ├── sync.py             # rclone sync
│   └── interactive.py      # Interactive mode
└── utils/
    ├── __init__.py
    ├── dates.py            # Date utilities
    └── display.py          # Terminal display utilities
```

## Key Features to Preserve

### 1. Entry Types and Signifiers
- Tasks: `[ ]`, `[x]`, `[>]`, `[<]`, `[~]`
- Events: `○`
- Notes: `-`
- Signifiers: `*` (priority), `!` (inspiration), `?` (explore), `@` (waiting), `#` (delegated)

### 2. Log Types
- **Daily Log**: Entries for today, indexed by date
- **Monthly Log**: Month-level tasks and events
- **Future Log**: Tasks scheduled for future months
- **Collections**: Named projects/lists

### 3. Migration System
- Tasks can be migrated forward (daily → daily, daily → collection)
- Tasks can be scheduled (daily → future)
- Migration history tracked

### 4. Habit Tracking
- Flexible frequencies: daily, weekly:N, monthly:N, days:mon,wed,fri
- Streak calculation
- Display in daily log

### 5. Export System (Enhanced)
Flexible PDF exports:
```bash
bujo export                           # Everything
bujo export --today                   # Just today
bujo export --date 2025-12-01         # Specific day
bujo export --week                    # This week
bujo export --month 2025-12           # Specific month
bujo export --collection "Project X"  # Single collection
bujo export --habits                  # Habit report
bujo export --habits --month 2025-12  # Habits for month
bujo export --from 2025-01-01 --to 2025-12-31  # Date range
```

### 6. Sync System (rclone-based)
```bash
bujo push                 # Upload DB to remote
bujo pull                 # Download DB from remote
bujo sync                 # Pull then push
```

Configuration in `config.toml`:
```toml
[sync]
remote = "s3:my-bucket/bujo"
# or "drive:bujo" or any rclone remote
```

**Conflict strategy**: Last-write-wins with backup. The pull command:
1. Backs up local DB
2. Downloads remote DB
3. Replaces local (simple strategy)

For more sophisticated merge, we can implement field-level merge later.

## CLI Commands

```
DAILY OPERATIONS
  bujo                          Interactive mode (default)
  bujo add "Task text"          Add task to today
  bujo add -e "Event"           Add event to today
  bujo add -n "Note"            Add note to today
  bujo add -p "Priority task"   Add priority task
  bujo add -c "Collection" "Task"  Add to collection

VIEWING
  bujo day [date]               View daily log
  bujo week [date]              View week
  bujo month [month]            View monthly log
  bujo future                   View future log
  bujo collection [name]        View/list collections

TASK MANAGEMENT
  bujo complete <id>            Mark task complete
  bujo cancel <id>              Cancel task
  bujo migrate <id> [dest]      Migrate task
  bujo schedule <id> <month>    Schedule to future

HABITS
  bujo habit add "Name" --freq daily
  bujo habit log "Name"
  bujo habit list
  bujo habit stats [name]
  bujo habit pause/resume/quit/complete "Name"

SEARCH & STATS
  bujo search "query"           Full-text search
  bujo tasks [--status open]    List tasks
  bujo stats                    Statistics

COLLECTIONS
  bujo collection new "Name"    Create collection
  bujo collection list          List collections
  bujo collection archive "Name"  Archive collection

EXPORT
  bujo export [options]         Export to PDF

SYNC
  bujo push                     Upload to remote
  bujo pull                     Download from remote
  bujo sync                     Pull + push

ADMIN
  bujo init                     Initialize database
  bujo undo                     Undo last action
  bujo config                   Edit config
```

## Interactive Mode

Same as current, but with habit quick-logging:

```
CLIBuJo                                         December 02, 2025
═══════════════════════════════════════════════════════════════════
  [ ] [1] Buy groceries
  [ ] [2] Review PR
  ○       Meeting at 3pm
  - Team decided on new architecture

─── Habits ────────────────────────────────────────────────────────
  ● [1] Exercise (streak: 5)
  ○ [2] Read 30min
  ○ [3] Meditate
───────────────────────────────────────────────────────────────────
[a]dd [x]complete [>]migrate [h]abit [/]search [q]uit
>
```

Commands:
- `a` - Add entry
- `x1` - Complete task 1
- `h1` - Log habit 1
- `>1` - Migrate task 1
- `/query` - Search
- `q` - Quit

## Migration from v1

```bash
bujo migrate-from-markdown /path/to/old/data
```

This will:
1. Read all markdown files
2. Parse entries using existing parser
3. Insert into new database
4. Preserve dates and collections

## Implementation Order

1. **Core Database** (`db.py`, `models.py`)
   - Schema creation
   - Connection management
   - Basic model dataclasses

2. **Entry Operations** (`entries.py`)
   - CRUD for entries
   - FTS integration
   - Date/collection filtering

3. **Habit System** (`habits.py`)
   - Port from current implementation
   - Streak calculation
   - Frequency handling

4. **Collections** (`collections.py`)
   - Collection CRUD
   - Archive functionality

5. **Migration System** (`migrations.py`)
   - Task migration
   - History tracking

6. **Undo System** (`undo.py`)
   - Multi-level undo
   - Action recording

7. **CLI Commands**
   - View commands (day, week, month)
   - Add commands
   - Task management
   - Habit commands
   - Search/stats

8. **Interactive Mode**
   - Port from current with simplifications

9. **Export System**
   - PDF generation with flexible filtering
   - Habit reports

10. **Sync System**
    - rclone integration
    - Push/pull/sync commands

11. **Data Migration Tool**
    - Import from markdown v1

12. **Tests**
    - Unit tests for all operations
    - Integration tests

## Configuration

`~/.local/share/bujo/config.toml`:

```toml
[sync]
remote = ""  # e.g., "s3:bucket/bujo" or "drive:bujo"

[display]
week_start = "monday"  # or "sunday"
date_format = "%B %d, %Y"
show_completed_habits = true

[habits]
show_in_daily = true
```

## Design Decisions (Confirmed)

1. **Undo levels**: 50 levels - good balance of history and storage
2. **Sync conflict**: Last-write-wins - simpler, newer timestamp wins
3. **Entry IDs**: Numeric for simplicity in display
4. **Archive**: Archived collections queryable with `--archived` flag
5. **PDF library**: fpdf2 - pure Python, easy install everywhere

## Dependencies

```toml
[project]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "prompt-toolkit>=3.0.0",
    "python-dateutil>=2.8.0",
]

[project.optional-dependencies]
export = [
    "fpdf2>=2.7.0",  # Simpler than weasyprint, no system deps
]
```

Note: Switching from weasyprint to fpdf2 for PDF export - it's pure Python with no system dependencies, making it easier to install on Termux/WSL.
