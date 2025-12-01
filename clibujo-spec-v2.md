# CLIBuJo — CLI Bullet Journal (v2)

## Project Overview

Build a command-line bullet journal implementing Ryder Carroll's Bullet Journal method. The app must work identically on Arch Linux (WSL) and Termux (Android), with git-based synchronization between devices.

### Core Philosophy

- **Near-analogue experience**: Typing, not clicking. Minimal UI, maximum speed.
- **Intentional friction**: Migration requires manual review — this is a feature.
- **Plain text source of truth**: Human-readable markdown files, editable outside the app.
- **Fast search via index**: SQLite cache for structured queries, rebuilt from markdown.
- **Offline-first**: Works without network; sync is explicit.

---

## Architecture: Hybrid Storage

### Why Hybrid?

| Concern | Markdown Files | SQLite |
|---------|---------------|--------|
| Search speed | Fast enough (grep) | Very fast (indexed) |
| Structured queries | Painful | Easy |
| Human readable | Yes, any editor | No, need the app |
| Git sync | Clean diffs, mergeable | Binary blob, conflicts = disaster |
| Debugging | Open in vim | Need tooling |

**Solution**: Markdown is the source of truth (syncs via git). SQLite is a local index (never synced, rebuilt from markdown).

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         WRITE PATH                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   User Input ──→ Parse ──→ Write Markdown ──→ Update SQLite    │
│                               │                    │            │
│                               ▼                    ▼            │
│                          data/*.md            cache.db          │
│                         (git synced)        (local only)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         READ PATH                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Simple View ──→ Read Markdown directly (fast for single day) │
│                                                                 │
│   Search/Query ──→ Query SQLite ──→ Return results with refs   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         SYNC PATH                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   git pull ──→ Detect changed .md files ──→ Reindex affected   │
│                                                                 │
│   Full rebuild: ~2-3 sec for 5 years of data (startup only)    │
│   Incremental:  ~instant (only changed files)                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Symbol Language

```
ENTRY TYPES
───────────────────────────────────────────────────────────
[ ]  Task           Something to do
 ○   Event          Date-related entry (past or scheduled)
 -   Note           Fact, idea, thought, observation

TASK STATES (task symbol transforms)
───────────────────────────────────────────────────────────
[ ]  Open           Not yet done
[x]  Complete       Done
[>]  Migrated       Moved forward to future month/collection
[<]  Scheduled      Moved to Future Log
[~]  Cancelled      No longer relevant

SIGNIFIERS (prefix, placed before entry symbol)
───────────────────────────────────────────────────────────
 *   Priority       Important, do first
 !   Inspiration    Great idea, insight, mantra
 ?   Explore        Needs research/followup
```

### Parsing Rules

Signifiers MUST be followed by an entry type marker. A bare `*` or `!` without a subsequent `[ ]`, `○`, or `-` is not a valid entry.

Valid examples:
```
* [ ] Priority task
! - Inspiration note
? ○ Event to explore
```

Invalid (will be ignored by parser):
```
* Just some text with asterisk
! Standalone exclamation
```

---

## Data Structure

### File Layout

```
~/.bujo/
├── config.yaml            # User configuration
├── cache.db               # SQLite index (LOCAL ONLY - in .gitignore)
├── data/                  # All synced content lives here
│   ├── index.md           # Master index (auto-generated)
│   ├── future.md          # Future log (months beyond current)
│   ├── months/
│   │   ├── 2024-12.md     # Monthly log: calendar + task list
│   │   └── 2025-01.md
│   ├── daily/
│   │   ├── 2024-12-01.md  # Daily log entries
│   │   ├── 2024-12-02.md
│   │   └── 2024-12-03.md
│   └── collections/
│       ├── projects/
│       │   └── taskquest.md
│       ├── trackers/
│       │   └── climbing.md
│       └── lists/
│           └── books.md
└── .git/                  # Git repo for sync
```

### .gitignore

```gitignore
# Local cache - never sync
cache.db
cache.db-journal
cache.db-wal
cache.db-shm

# Editor artifacts
*.swp
*~
.DS_Store
```

### Markdown File Formats

**Daily Log (`data/daily/2024-12-03.md`):**

Entries are NOT indented. Each entry starts at column 0. Indentation has no semantic meaning and should not be used.

```markdown
# December 3, 2024

* [ ] Call Urban Utilities about interview
[ ] Review Taskwarrior sync setup
[x] Grocery shopping
[ ] Research Flutter state management
○ Rock climbing session 6pm
- TaskQuest could use habit streaks as XP multiplier
! - "The friction IS the feature"
[>] Fix WSL network issue →monthly/2024-12
```

**Monthly Log (`data/months/2024-12.md`):**
```markdown
# December 2024

## Calendar

01 Su
02 Mo  Interview prep
03 Tu  Urban Utilities call
04 We
05 Th  Climbing
06 Fr
07 Sa
08 Su
09 Mo
10 Tu  Dentist 2pm
...
25 We  Christmas
...
31 Tu  New Years Eve

## Tasks

[ ] Finalize TaskQuest Flutter migration
[ ] Update resume for water utilities
[ ] Fix Termux sync scripts
[x] Submit job application - Seqwater
[ ] Research property staging costs
[>] Migrate photos from old phone →future/2025-02
```

**Future Log (`data/future.md`):**
```markdown
# Future Log

## January 2025

[ ] Uni semester starts (check dates)
○ Property settlement (tentative)
[ ] Annual health checkup

## February 2025

[ ] Renew driver's license

## March 2025

[ ] Tax prep - gather documents
[ ] TaskQuest v1.0 target release

## Someday

[ ] Learn Rust properly
[ ] Multi-day climbing trip
[ ] Build custom mechanical keyboard
```

**Collection (`data/collections/projects/taskquest.md`):**
```markdown
# TaskQuest Development

> Cross-platform gamified task manager

## Goals

- Cross-platform (Android + Desktop via Flutter)
- Sync with existing Taskwarrior data
- D&D-style character progression

## Architecture

- Use Riverpod for state management
- SQLite for local, Git for sync
- Keep Taskwarrior as source of truth

## Tasks

[x] Set up Flutter project structure
[x] Design data models
[ ] Build task list view
[ ] Implement XP calculation system
[ ] Create character stat display

## Notes

- Consider habit streaks as XP multiplier
- Look at how Habitica handles party system
```

**Index (`data/index.md`):** Auto-generated table of contents with entry counts.

---

## Entry Referencing

### The Problem

Entries need stable references for operations like complete, migrate, and cancel. But:
- Line numbers shift when files are edited
- SQLite IDs change on reindex
- We need something that survives both

### Solution: Content-Based References

Each entry gets a short hash based on: `source_file + original_line_content + creation_context`

```python
def entry_ref(source_file: str, content: str, entry_date: str) -> str:
    """Generate a stable 6-char reference for an entry."""
    data = f"{source_file}:{content}:{entry_date}"
    return hashlib.sha256(data.encode()).hexdigest()[:6]
```

In SQLite:
```sql
entry_ref TEXT UNIQUE NOT NULL  -- e.g., "a3f2c1"
```

In display:
```
* [ ] [a3f2c1] Call Urban Utilities about interview
  [ ] [b7e4d2] Review Taskwarrior sync setup
```

Commands use refs:
```bash
bujo complete a3f2c1
bujo migrate b7e4d2 future
```

For convenience, in interactive mode, temporary numeric indices `[1]`, `[2]` map to refs for the current session only.

---

## Migration Tracking

### The Problem

When a task is migrated (`[>]`), we need to:
1. Mark the original as migrated
2. Create the new entry in the destination
3. Link them bidirectionally

### Solution: Migration Annotations

When migrating, append a destination hint to the original:
```markdown
[>] Fix WSL network issue →monthly/2024-12
```

And in the destination, add a source hint:
```markdown
[ ] Fix WSL network issue ←daily/2024-11-15
```

These hints are:
- Human-readable in the markdown
- Parsed into `migrated_to` and `migrated_from` fields in SQLite
- Used to show migration chains: `bujo history a3f2c1`

### Migration as Atomic Operation

```python
def migrate_task(entry_ref: str, destination: str):
    """Migrate a task atomically."""

    # 1. Find the entry
    entry = db.get_entry(entry_ref)

    # 2. Update source file: [ ] → [>] with destination hint
    update_line_in_file(
        entry.source_file,
        entry.line_number,
        mark_migrated(entry.raw_line, destination)
    )

    # 3. Append to destination file with source hint
    append_to_file(
        destination,
        create_migrated_entry(entry.content, entry.source_file)
    )

    # 4. Reindex both files
    reindex_file(entry.source_file)
    reindex_file(destination)
```

---

## SQLite Schema

### Database: `cache.db`

```sql
-- Core entries table
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_ref TEXT UNIQUE NOT NULL,   -- Stable 6-char hash

    -- Source file reference
    source_file TEXT NOT NULL,        -- e.g., "daily/2024-12-03.md"
    line_number INTEGER NOT NULL,     -- Line in source file
    raw_line TEXT NOT NULL,           -- Original line for reconstruction

    -- Entry content
    entry_type TEXT NOT NULL,         -- 'task', 'event', 'note'
    status TEXT,                      -- 'open', 'complete', 'migrated', 'scheduled', 'cancelled'
    signifier TEXT,                   -- 'priority', 'inspiration', 'explore', NULL
    content TEXT NOT NULL,            -- The actual text (without markers)

    -- Temporal context
    entry_date DATE,                  -- Date entry belongs to
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,

    -- Organizational context
    collection TEXT,                  -- Collection name if applicable
    month TEXT,                       -- Month (YYYY-MM) for monthly log entries

    -- Migration tracking
    migrated_to TEXT,                 -- Destination file ref (parsed from →hint)
    migrated_from TEXT                -- Source file ref (parsed from ←hint)
);

-- Full-text search virtual table
CREATE VIRTUAL TABLE entries_fts USING fts5(
    content,
    content='entries',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
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

-- File tracking for incremental reindex
CREATE TABLE file_hashes (
    file_path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,       -- SHA256 of file content
    indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_entries_ref ON entries(entry_ref);
CREATE INDEX idx_entries_date ON entries(entry_date);
CREATE INDEX idx_entries_type ON entries(entry_type);
CREATE INDEX idx_entries_status ON entries(status);
CREATE INDEX idx_entries_collection ON entries(collection);
CREATE INDEX idx_entries_month ON entries(month);
CREATE INDEX idx_entries_source ON entries(source_file);
```

### Example Queries

```sql
-- Full-text search
SELECT e.*, snippet(entries_fts, 0, '>>>', '<<<', '...', 32) as snippet
FROM entries e
JOIN entries_fts ON e.id = entries_fts.rowid
WHERE entries_fts MATCH 'urban utilities'
ORDER BY rank;

-- All incomplete tasks
SELECT * FROM entries
WHERE entry_type = 'task' AND status = 'open'
ORDER BY entry_date DESC;

-- Tasks completed this month
SELECT * FROM entries
WHERE entry_type = 'task'
  AND status = 'complete'
  AND entry_date >= date('now', 'start of month')
ORDER BY completed_at;

-- Tasks in a specific collection
SELECT * FROM entries
WHERE collection = 'projects/taskquest'
  AND entry_type = 'task'
ORDER BY line_number;

-- Priority items from last 7 days
SELECT * FROM entries
WHERE signifier = 'priority'
  AND entry_date >= date('now', '-7 days')
ORDER BY entry_date DESC;

-- Migration chain for an entry
WITH RECURSIVE chain AS (
    SELECT * FROM entries WHERE entry_ref = 'a3f2c1'
    UNION ALL
    SELECT e.* FROM entries e
    JOIN chain c ON e.migrated_from LIKE '%' || c.source_file || '%'
)
SELECT * FROM chain;

-- Stats: completion rate by month
SELECT
    strftime('%Y-%m', entry_date) as month,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed,
    ROUND(100.0 * SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) / COUNT(*), 1) as completion_rate
FROM entries
WHERE entry_type = 'task'
GROUP BY month
ORDER BY month DESC;
```

---

## Indexing Logic

### Full Rebuild

Run on first startup or `bujo reindex --full`:

```python
def full_reindex():
    """Rebuild entire SQLite cache from markdown files."""

    # Clear existing data
    db.execute("DELETE FROM entries")
    db.execute("DELETE FROM file_hashes")

    # Walk all markdown files
    for md_file in walk_markdown_files(DATA_DIR):
        index_file(md_file)

    db.commit()
```

### Incremental Reindex

Run on startup and after sync:

```python
def incremental_reindex():
    """Only reindex files that changed since last index."""

    for md_file in walk_markdown_files(DATA_DIR):
        current_hash = hash_file(md_file)
        stored_hash = db.get_hash(md_file)

        if current_hash != stored_hash:
            # File changed - reindex it
            db.execute("DELETE FROM entries WHERE source_file = ?", md_file)
            index_file(md_file)
            db.update_hash(md_file, current_hash)

    # Clean up deleted files
    for stored_file in db.get_all_indexed_files():
        if not file_exists(stored_file):
            db.execute("DELETE FROM entries WHERE source_file = ?", stored_file)
            db.execute("DELETE FROM file_hashes WHERE file_path = ?", stored_file)

    db.commit()
```

### Markdown Parser

```python
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class Entry:
    entry_type: str      # 'task', 'event', 'note'
    status: Optional[str]  # 'open', 'complete', 'migrated', 'scheduled', 'cancelled'
    signifier: Optional[str]  # 'priority', 'inspiration', 'explore'
    content: str
    raw_line: str
    migrated_to: Optional[str] = None
    migrated_from: Optional[str] = None

# Regex patterns
SIGNIFIER_PATTERN = re.compile(r'^([*!?])\s+')
TASK_PATTERN = re.compile(r'^\[([ x><~])\]\s+(.+)')
EVENT_PATTERN = re.compile(r'^○\s*(.+)')
NOTE_PATTERN = re.compile(r'^-\s+(.+)')
MIGRATION_TO_PATTERN = re.compile(r'→(\S+)$')
MIGRATION_FROM_PATTERN = re.compile(r'←(\S+)$')

def parse_entry(line: str) -> Optional[Entry]:
    """Parse a single line into an Entry object."""

    raw_line = line
    line = line.strip()

    if not line or line.startswith('#'):
        return None

    # Check for signifier prefix
    signifier = None
    signifier_match = SIGNIFIER_PATTERN.match(line)
    if signifier_match:
        sig_char = signifier_match.group(1)
        signifier = {'*': 'priority', '!': 'inspiration', '?': 'explore'}[sig_char]
        line = line[signifier_match.end():]

    # Check for migration hints
    migrated_to = None
    migrated_from = None

    to_match = MIGRATION_TO_PATTERN.search(line)
    if to_match:
        migrated_to = to_match.group(1)
        line = line[:to_match.start()].strip()

    from_match = MIGRATION_FROM_PATTERN.search(line)
    if from_match:
        migrated_from = from_match.group(1)
        line = line[:from_match.start()].strip()

    # Parse entry type
    task_match = TASK_PATTERN.match(line)
    if task_match:
        status_char = task_match.group(1)
        status_map = {
            ' ': 'open',
            'x': 'complete',
            '>': 'migrated',
            '<': 'scheduled',
            '~': 'cancelled'
        }
        return Entry(
            entry_type='task',
            status=status_map[status_char],
            signifier=signifier,
            content=task_match.group(2),
            raw_line=raw_line,
            migrated_to=migrated_to,
            migrated_from=migrated_from
        )

    event_match = EVENT_PATTERN.match(line)
    if event_match:
        return Entry(
            entry_type='event',
            status=None,
            signifier=signifier,
            content=event_match.group(1),
            raw_line=raw_line
        )

    note_match = NOTE_PATTERN.match(line)
    if note_match:
        return Entry(
            entry_type='note',
            status=None,
            signifier=signifier,
            content=note_match.group(1),
            raw_line=raw_line
        )

    return None  # Not a recognized entry

def index_file(file_path: str):
    """Parse markdown file and insert entries into SQLite."""

    content = read_file(file_path)
    context = determine_context(file_path)

    for line_num, line in enumerate(content.splitlines(), 1):
        entry = parse_entry(line)
        if entry:
            ref = entry_ref(file_path, entry.content, context.date or '')
            db.execute("""
                INSERT INTO entries
                (entry_ref, source_file, line_number, raw_line, entry_type,
                 status, signifier, content, entry_date, collection, month,
                 migrated_to, migrated_from)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ref,
                file_path,
                line_num,
                entry.raw_line,
                entry.entry_type,
                entry.status,
                entry.signifier,
                entry.content,
                context.date,
                context.collection,
                context.month,
                entry.migrated_to,
                entry.migrated_from
            ))
```

---

## CLI Interface

### Primary Commands

```bash
bujo                    # Show today's daily log (default view)
bujo add <entry>        # Quick add to today (auto-detect type from prefix)
bujo add -t "task"      # Add task
bujo add -e "event"     # Add event
bujo add -n "note"      # Add note

bujo day [date]         # View/edit specific day (default: today)
bujo week               # View current week summary
bujo month [month]      # View/edit monthly log

bujo future             # View/edit future log
bujo index              # View index

bujo collection <name>  # View/edit collection
bujo collection new <name> [--type=project|tracker|list]
bujo collections        # List all collections

bujo complete <ref>     # Mark task complete [x]
bujo cancel <ref>       # Mark task cancelled [~]
bujo migrate <ref> [dest]  # Migrate task (interactive if no dest)
bujo schedule <ref> <month>  # Schedule to future log
bujo history <ref>      # Show migration chain for an entry

bujo migration          # Start monthly migration wizard

bujo sync               # Git pull, commit, push
bujo reindex            # Rebuild SQLite cache (incremental)
bujo reindex --full     # Full rebuild of SQLite cache

# Search commands (use SQLite FTS)
bujo search <query>     # Full-text search (default, always uses FTS)
bujo tasks [--status=open|complete|all] [--collection=X] [--from=DATE] [--to=DATE]
bujo stats [--year=YYYY] [--month=MM]
```

### Quick Add Syntax

The `add` command auto-detects entry type from prefix:

```bash
bujo add "[ ] Buy groceries"        # Task
bujo add "* [ ] Urgent deadline"    # Priority task
bujo add "○ Meeting at 3pm"         # Event
bujo add "- Interesting thought"    # Note
bujo add "! - Great insight"        # Inspiration note
bujo add "? [ ] Research this"      # Explore task
```

If no prefix detected, default to task (most common use case).

### Interactive Mode

Running `bujo` with no args enters interactive mode:

```
CLIBuJo                                         Dec 3, 2024

═══ TODAY ═══════════════════════════════════════════════════

* [ ] [1] Call Urban Utilities about interview
  [ ] [2] Review Taskwarrior sync setup
  [x] [3] Grocery shopping
  [ ] [4] Research Flutter state management
  ○   [5] Rock climbing session 6pm
  -       TaskQuest could use habit streaks
! -       "The friction IS the feature"

──────────────────────────────────────────────────────────────
[a]dd [x]complete [>]migrate [c]ollection [m]onth [f]uture [/]search [s]ync [q]uit

> _
```

Notes and events without actionable state don't get index numbers (they can't be completed/migrated).

Single-key commands for speed:
- `a` — Add entry (prompts for type and content)
- `x 1` — Complete task 1
- `> 2` — Migrate task 2 (prompts for destination)
- `~ 3` — Cancel task 3
- `c` — List/select collections
- `m` — View monthly log
- `f` — View future log
- `/` — Search mode (uses SQLite FTS)
- `s` — Sync (git pull/push)
- `e` — Open today's file in $EDITOR
- `q` — Quit

### Adaptive Display Width

Detect terminal width and format accordingly:

```python
import shutil

def get_display_width() -> int:
    """Get terminal width, with sensible defaults."""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80  # Safe default for Termux

def truncate_for_display(text: str, max_width: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_width:
        return text
    return text[:max_width-3] + "..."
```

For narrow terminals (< 60 cols), use compact mode:
- Shorter headers
- No box-drawing characters
- Abbreviated dates

### Search Mode

```
> /

Search: urban utilities

Found 7 results:

[1] 2024-12-03 daily    * [ ] Call Urban Utilities about interview
[2] 2024-12-02 daily      [x] Research Urban Utilities job posting
[3] 2024-11-28 daily      -   Urban Utilities uses SAP for maintenance
[4] 2024-11-25 daily      [ ] Update resume for Urban Utilities
[5] job-search collection [ ] Apply to Urban Utilities senior role
[6] job-search collection -   Urban Utilities interview process: 2 rounds
[7] 2024-11-20 daily      ○   Urban Utilities info session

[number] to jump, [Enter] to return: 1

Opening daily/2024-12-03.md in $EDITOR...
```

### Stats Command

```bash
$ bujo stats --year=2024

CLIBuJo Stats: 2024

Tasks Overview
──────────────────────────────────────
Total tasks:     847
Completed:       612 (72.3%)
Migrated:        89  (10.5%)
Cancelled:       43  (5.1%)
Still open:      103 (12.2%)

Monthly Breakdown
──────────────────────────────────────
         Tasks  Done  Rate
Jan 24     67    52   78%
Feb 24     71    55   77%
Mar 24     83    61   73%
...
Dec 24     23    12   52%  (in progress)

Most Active Collections
──────────────────────────────────────
job-search:     34 tasks (28 complete)
taskquest:      47 tasks (31 complete)
home-reno:      22 tasks (19 complete)
```

### Migration Wizard

`bujo migration` starts an interactive review:

```
Monthly Migration: November 2024 → December 2024

Reviewing 23 incomplete tasks...

[1/23] [ ] Fix WSL network issue
       Source: daily/2024-11-15.md
       Age: 18 days

       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: k

       → Migrated to December 2024

[2/23] [ ] Learn Rust basics
       Source: daily/2024-11-08.md
       Age: 25 days

       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: f

       Which month? (1-12, or 'someday'): someday

       → Scheduled to Someday

[3/23] [ ] Buy Dave's birthday gift
       Source: daily/2024-11-22.md
       Age: 11 days

       This task is old. Still relevant?
       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: d

       → Dropped (marked [~])

...

Migration complete!
  Kept:      15
  Future:     4
  Collection: 2
  Dropped:    2

Updating index...
December 2024 monthly log updated.
```

---

## Configuration

**`~/.bujo/config.yaml`:**
```yaml
# CLIBuJo Configuration

# Editor for full-page editing
editor: nvim

# Date format
date_format: "%B %d, %Y"  # December 03, 2024
short_date: "%b %d"       # Dec 03

# First day of week (0=Monday, 6=Sunday)
week_start: 0

# Display
narrow_threshold: 60      # Use compact mode below this width
show_entry_refs: false    # Show [a3f2c1] refs (true) or [1] indices (false)

# Sync settings
sync:
  enabled: true
  remote: origin
  branch: main
  auto_pull: true         # Pull on startup
  auto_push: false        # Require explicit sync

# Index settings
index:
  auto_reindex: true      # Incremental reindex on startup
  reindex_on_sync: true   # Reindex after git pull

# Default collection types
collection_types:
  - project
  - tracker
  - list

# Custom signifiers (extend defaults)
# Parser must be made config-aware to support these
signifiers:
  "@": "waiting"          # Waiting on someone
  "#": "delegated"        # Delegated to someone
```

### Config-Aware Parser

To support custom signifiers from config:

```python
def load_signifiers(config: dict) -> dict:
    """Load signifiers from config, merging with defaults."""
    defaults = {
        '*': 'priority',
        '!': 'inspiration',
        '?': 'explore'
    }
    custom = config.get('signifiers', {})
    return {**defaults, **custom}

# In parser initialization
SIGNIFIERS = load_signifiers(config)
SIGNIFIER_CHARS = ''.join(re.escape(c) for c in SIGNIFIERS.keys())
SIGNIFIER_PATTERN = re.compile(rf'^([{SIGNIFIER_CHARS}])\s+')
```

---

## Sync Strategy

### Git-Based Sync

The `~/.bujo/data` directory is tracked by git. Sync uses simple git operations:

```bash
bujo sync
```

Performs:
1. `git pull --rebase origin main`
2. If conflicts: mark files, notify user, abort push
3. If clean: `git add -A`
4. `git commit -m "sync: <device> <timestamp>"`
5. `git push origin main`
6. Run incremental reindex

### Conflict Handling

**Daily logs**: Rarely conflict (append-only pattern).

**Monthly logs & collections**: Can conflict on edits in the middle of files.

Strategy:
1. Detect conflicts after pull
2. Keep both versions with git conflict markers
3. Show clear message: "Conflict in monthly/2024-12.md — please resolve"
4. Block sync until resolved
5. After user resolves: `bujo sync` again

```python
def sync():
    """Perform git sync with conflict detection."""

    # Pull with rebase
    result = run_git(['pull', '--rebase', 'origin', config.sync.branch])

    if has_conflicts():
        conflicted = get_conflicted_files()
        print(f"Conflicts detected in {len(conflicted)} file(s):")
        for f in conflicted:
            print(f"  - {f}")
        print("\nResolve conflicts manually, then run 'bujo sync' again.")
        return False

    # Stage and commit
    run_git(['add', '-A'])

    if has_staged_changes():
        device = get_device_name()
        timestamp = datetime.now().isoformat()
        run_git(['commit', '-m', f'sync: {device} {timestamp}'])
        run_git(['push', 'origin', config.sync.branch])

    # Reindex changed files
    incremental_reindex()

    return True
```

### Startup Flow

```python
def startup():
    # 1. Auto-pull if configured
    if config.sync.enabled and config.sync.auto_pull:
        try:
            git_pull()
        except GitError as e:
            print(f"Warning: Could not pull: {e}")

    # 2. Check/build cache
    if not cache_db_exists():
        print("First run — building index...")
        full_reindex()
    elif config.index.auto_reindex:
        changed = incremental_reindex()
        if changed:
            print(f"Reindexed {changed} file(s)")

    # 3. Show today's log
    show_daily_log(today())
```

---

## Technical Requirements

### Language & Dependencies

**Python 3.10+**

Rationale:
- Available on both Arch and Termux
- Rich ecosystem for CLI (Typer, Rich, Prompt Toolkit)
- SQLite built-in
- Fast enough for this use case
- Easy to hack/extend

### Key Libraries

```
typer           # CLI framework
rich            # Terminal formatting, tables
prompt-toolkit  # Interactive input, keybindings
pyyaml          # Config parsing
python-dateutil # Date parsing/manipulation
# sqlite3 is built-in
# subprocess for git (simpler than GitPython)
```

### Installation

```bash
# From repo
git clone <repo> ~/.bujo-app
cd ~/.bujo-app
pip install -e .

# Or via pipx
pipx install clibujo
```

Creates `bujo` command in PATH.

### Platform-Specific Notes

**Arch Linux (WSL):**
- Standard Python environment
- Git available via pacman
- No special considerations

**Termux (Android):**
- `pkg install python git`
- Storage at `~/.bujo` (Termux home)
- May need `termux-setup-storage` for external access
- Typically narrower terminal — test compact mode
- Consider touch-friendly keybindings in future

---

## Implementation Phases

### Phase 1: Core Foundation (MVP target)
- [ ] Project structure and config loading
- [ ] SQLite schema setup and connection
- [ ] Markdown parser (entries, types, signifiers, migration hints)
- [ ] Entry reference generation
- [ ] File I/O utilities
- [ ] Full reindex from markdown → SQLite
- [ ] Incremental reindex logic

### Phase 2: Daily Operations
- [ ] `bujo` — Show today's daily log
- [ ] `bujo add` — Quick capture
- [ ] `bujo complete` / `bujo cancel` (with entry refs)
- [ ] `bujo day [date]` — View specific day
- [ ] Interactive mode (basic)

### Phase 3: Logs & Structure
- [ ] Monthly log: view, edit, calendar generation
- [ ] Future log: view, edit
- [ ] Week view
- [ ] Index auto-generation

### Phase 4: Collections
- [ ] Collection CRUD
- [ ] Collection types (project, tracker, list)
- [ ] List all collections

### Phase 5: Search & Query (v1.0 target)
- [ ] Full-text search via FTS5
- [ ] `bujo search <query>`
- [ ] `bujo tasks` with filters
- [ ] `bujo stats`

### Phase 6: Migration
- [ ] Monthly migration wizard
- [ ] Task state transitions in files (`[>]`, `[<]`, `[~]`)
- [ ] Migration hints (→ and ←)
- [ ] `bujo history` command
- [ ] Cross-file migration (daily → collection)

### Phase 7: Sync & Polish
- [ ] Git sync integration
- [ ] Conflict detection and handling
- [ ] Auto-reindex after sync
- [ ] Termux compatibility testing
- [ ] Adaptive display width
- [ ] Interactive mode refinement

### Future Enhancements (post-v1)
- [ ] Undo last action
- [ ] Entry editing (open in $EDITOR at specific line)
- [ ] Templates for new collections
- [ ] Custom signifiers from config
- [ ] Export (to PDF, HTML)

---

## Testing Checklist

### Functional Tests
- [ ] Create new bujo from scratch (empty data dir)
- [ ] Full reindex builds correct SQLite data
- [ ] Entry refs are stable across reindex
- [ ] Add tasks, events, notes to daily log
- [ ] Complete and cancel tasks (file updated correctly)
- [ ] Create monthly log, add calendar events
- [ ] Add items to future log
- [ ] Create collections of each type
- [ ] Run monthly migration
- [ ] Migration hints are written and parsed correctly
- [ ] Search finds entries across all files
- [ ] Stats calculations are accurate

### Sync Tests
- [ ] Sync between two devices (simulate with two directories)
- [ ] Incremental reindex detects file changes
- [ ] Conflict detection works
- [ ] User can resolve and re-sync
- [ ] Deleted files are removed from index

### Platform Tests
- [ ] Works in 80-column terminal (standard)
- [ ] Works in 40-column terminal (Termux compact)
- [ ] Works with minimal color support
- [ ] SQLite works on Termux
- [ ] Git operations work on both platforms

### Edge Cases
- [ ] Empty files don't crash parser
- [ ] Malformed entries are skipped gracefully
- [ ] Invalid signifiers (bare `*`) don't create entries
- [ ] Very long entries (>1000 chars)
- [ ] Unicode content (emoji, CJK)
- [ ] 5 years of simulated data (performance test)
- [ ] Entry with same content on same day gets unique ref

---

## Example Session

```bash
$ bujo
CLIBuJo                                         Dec 3, 2024

Reindexing... 3 files changed.

═══ TODAY ═══════════════════════════════════════════════════

  (empty day — start logging!)

> a
Type [t]ask [e]vent [n]ote: t
Priority? [y/N]: y
> Call Urban Utilities about interview

Added: * [ ] Call Urban Utilities about interview

> a
Type [t]ask [e]vent [n]ote: t
Priority? [y/N]: n
> Review Taskwarrior sync setup

Added: [ ] Review Taskwarrior sync setup

> [ ] Quick task via prefix

Added: [ ] Quick task via prefix

> x 3

Completed: [x] Quick task via prefix

> /
Search: taskquest

Found 12 results:

[1] 2024-12-01 daily      [ ] Work on TaskQuest Flutter migration
[2] 2024-11-28 daily      [x] Design TaskQuest XP system
[3] taskquest  collection [ ] Build task list view
...

[Enter] to return:

> s

Syncing...
  ✓ Pulled 2 changes
  ✓ Reindexed 2 files
  ✓ Committed: "sync: wsl 2024-12-03T10:42:00"
  ✓ Pushed to origin/main

> q

$ bujo stats

CLIBuJo Stats: December 2024

Tasks: 23 total, 15 complete (65%)
Top collection: job-search (8 tasks)

$
```

---

## Notes for Implementation

1. **SQLite cache is disposable** — Can always be rebuilt from markdown. Never sync it.

2. **Markdown is authoritative** — If there's ever a mismatch, markdown wins.

3. **Entry refs must be deterministic** — Same content + file + date = same ref, even across devices.

4. **Test on both platforms early** — Don't leave Termux compatibility to the end.

5. **FTS5 is the only search** — No separate grep fallback. SQLite FTS handles everything.

6. **Incremental reindex must be fast** — Hash comparison, not content parsing.

7. **Keep markdown human-editable** — Users will vim their files directly. Migration hints must be unobtrusive.

8. **Shell out to git** — subprocess is simpler and more portable than GitPython.

9. **No indentation semantics** — Unlike the original, entries don't nest. Keeps parsing simple.

10. **Git history is the backup** — No separate backup strategy needed.

The goal is a tool that feels as fast and immediate as writing in a notebook, but with the searchability of a database and the sync of git. Prioritize speed of capture above all else.
