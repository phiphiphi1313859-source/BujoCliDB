# CLIBuJo — CLI Bullet Journal

## Project Overview

Build a command-line bullet journal application implementing Ryder Carroll's Bullet Journal method. The app must work identically on Arch Linux (WSL) and Termux (Android), with git-based synchronization between devices.

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
| Obsidian compatible | Yes | No |
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

SIGNIFIERS (prefix, placed before entry)
───────────────────────────────────────────────────────────
 *   Priority       Important, do first
 !   Inspiration    Great idea, insight, mantra
 ?   Explore        Needs research/followup
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
```markdown
# December 3, 2024

* [ ] Call Urban Utilities about interview
  [ ] Review Taskwarrior sync setup
  [x] Grocery shopping
  [ ] Research Flutter state management
  ○   Rock climbing session 6pm
  -   TaskQuest could use habit streaks as XP multiplier
! -   "The friction IS the feature"
  [>] Fix WSL network issue
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
[>] Migrate photos from old phone
```

**Future Log (`data/future.md`):**
```markdown
# Future Log

## January 2025

[ ] Uni semester starts (check dates)
○   Property settlement (tentative)
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

## SQLite Schema

### Database: `cache.db`

```sql
-- Core entries table
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Source file reference
    source_file TEXT NOT NULL,        -- e.g., "daily/2024-12-03.md"
    line_number INTEGER,              -- Line in source file
    
    -- Entry content
    entry_type TEXT NOT NULL,         -- 'task', 'event', 'note'
    status TEXT,                      -- 'open', 'complete', 'migrated', 'scheduled', 'cancelled'
    signifier TEXT,                   -- 'priority', 'inspiration', 'explore', NULL
    content TEXT NOT NULL,            -- The actual text
    
    -- Temporal context
    entry_date DATE,                  -- Date entry belongs to
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    
    -- Organizational context
    collection TEXT,                  -- Collection name if applicable
    month TEXT,                       -- Month (YYYY-MM) for monthly log entries
    
    -- Metadata
    migrated_to TEXT,                 -- Where it was migrated (file ref)
    migrated_from TEXT                -- Where it came from (file ref)
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
def index_file(file_path: str):
    """Parse markdown file and insert entries into SQLite."""
    
    content = read_file(file_path)
    context = determine_context(file_path)  # daily/monthly/collection/future
    
    for line_num, line in enumerate(content.splitlines(), 1):
        entry = parse_entry(line)
        if entry:
            db.execute("""
                INSERT INTO entries 
                (source_file, line_number, entry_type, status, signifier, 
                 content, entry_date, collection, month)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_path,
                line_num,
                entry.type,
                entry.status,
                entry.signifier,
                entry.content,
                context.date,
                context.collection,
                context.month
            ))

def parse_entry(line: str) -> Optional[Entry]:
    """Parse a single line into an Entry object."""
    
    line = line.strip()
    if not line:
        return None
    
    # Detect signifiers (prefix)
    signifier = None
    if line.startswith('* '):
        signifier = 'priority'
        line = line[2:]
    elif line.startswith('! '):
        signifier = 'inspiration'
        line = line[2:]
    elif line.startswith('? '):
        signifier = 'explore'
        line = line[2:]
    
    # Detect entry type and status
    if line.startswith('[ ] '):
        return Entry('task', 'open', signifier, line[4:])
    elif line.startswith('[x] '):
        return Entry('task', 'complete', signifier, line[4:])
    elif line.startswith('[>] '):
        return Entry('task', 'migrated', signifier, line[4:])
    elif line.startswith('[<] '):
        return Entry('task', 'scheduled', signifier, line[4:])
    elif line.startswith('[~] '):
        return Entry('task', 'cancelled', signifier, line[4:])
    elif line.startswith('○'):
        return Entry('event', None, signifier, line[1:].strip())
    elif line.startswith('-'):
        return Entry('note', None, signifier, line[1:].strip())
    
    return None  # Not a recognized entry (probably a header or prose)
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

bujo complete <id>      # Mark task complete [x]
bujo cancel <id>        # Mark task cancelled [~]
bujo migrate <id> [dest]  # Migrate task (interactive if no dest)
bujo schedule <id> <month>  # Schedule to future log

bujo migration          # Start monthly migration wizard

bujo sync               # Git pull, commit, push
bujo reindex            # Rebuild SQLite cache (incremental)
bujo reindex --full     # Full rebuild of SQLite cache

# Search commands (use SQLite)
bujo search <query>                    # Full-text search
bujo tasks [--status=open|complete|all] [--collection=X] [--from=DATE] [--to=DATE]
bujo stats [--year=YYYY] [--month=MM]  # Completion stats
bujo grep <pattern>                    # Raw grep fallback (direct on files)
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

If no prefix detected, prompt for type or default to task.

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

Single-key commands for speed:
- `a` — Add entry (prompts for type and content)
- `x 1` — Complete task 1
- `> 2` — Migrate task 2 (prompts for destination)
- `c` — List/select collections
- `m` — View monthly log
- `f` — View future log
- `/` — Search mode (uses SQLite FTS)
- `s` — Sync (git pull/push)
- `q` — Quit

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

Jumping to daily/2024-12-03.md...
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
Apr 24     69    48   70%
May 24     72    54   75%
Jun 24     78    52   67%
Jul 24     81    59   73%
Aug 24     74    56   76%
Sep 24     82    61   74%
Oct 24     79    55   70%
Nov 24     68    47   69%
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
       
       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: k
       
       → Migrated to December 2024

[2/23] [ ] Learn Rust basics
       Source: daily/2024-11-08.md
       
       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: f
       
       Which month? (1-12, or 'someday'): someday
       
       → Scheduled to Someday

[3/23] [ ] Buy Dave's birthday gift
       Source: daily/2024-11-22.md
       
       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: d
       
       → Dropped

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
signifiers:
  "@": "waiting"          # Waiting on someone
  "#": "delegated"        # Delegated to someone
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
2. Auto-resolve simple conflicts (append both versions with conflict markers)
3. `git add -A`
4. `git commit -m "sync: <device> <timestamp>"`
5. `git push origin main`
6. Run incremental reindex (update SQLite from any pulled changes)

### Conflict Handling

For markdown files, conflicts are rare (append-only daily logs). When they occur:

1. Keep both versions with clear markers
2. Notify user: "Conflict in daily/2024-12-03.md — please review"
3. User resolves manually and runs `bujo sync` again
4. Reindex runs automatically after resolution

### Startup Flow

```python
def startup():
    # 1. Auto-pull if configured
    if config.sync.auto_pull:
        git_pull()
    
    # 2. Check if cache exists
    if not cache_db_exists():
        full_reindex()  # First run
    else:
        incremental_reindex()  # Update from any changes
    
    # 3. Show today's log
    show_daily_log(today())
```

---

## Technical Requirements

### Language & Dependencies

**Recommended: Python 3.10+**

Rationale:
- Available on both Arch and Termux
- Rich ecosystem for CLI (Typer, Rich, Prompt Toolkit)
- SQLite built-in
- Fast enough for this use case
- Easy to hack/extend

**Alternative: Rust**
- If performance/portability is paramount
- Clap for CLI, rusqlite for SQLite

### Key Libraries (Python)

```
typer           # CLI framework
rich            # Terminal formatting, tables, markdown
prompt-toolkit  # Interactive input, keybindings
pyyaml          # Config parsing
python-dateutil # Date parsing/manipulation
gitpython       # Git operations (or shell out to git)
# sqlite3 is built-in
```

### Installation

Should be installable via:

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
- SQLite available (python built-in)
- No special considerations

**Termux (Android):**
- `pkg install python git`
- Storage at `~/.bujo` (Termux home)
- SQLite works fine in Termux
- May need `termux-setup-storage` for external access
- Consider smaller terminal width in formatting

---

## Implementation Phases

### Phase 1: Core Foundation
- [ ] Project structure and config loading
- [ ] SQLite schema setup and connection
- [ ] Markdown parser (entries, types, signifiers)
- [ ] File I/O utilities
- [ ] Full reindex from markdown → SQLite
- [ ] Incremental reindex logic

### Phase 2: Daily Operations
- [ ] `bujo` — Show today's daily log
- [ ] `bujo add` — Quick capture
- [ ] `bujo complete` / `bujo cancel`
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
- [ ] Threading support

### Phase 5: Search & Query
- [ ] Full-text search via FTS5
- [ ] `bujo search <query>`
- [ ] `bujo tasks` with filters
- [ ] `bujo stats`

### Phase 6: Migration
- [ ] Monthly migration wizard
- [ ] Task state transitions in files (`[>]`, `[<]`, `[~]`)
- [ ] Cross-file migration (daily → collection)
- [ ] Migration history

### Phase 7: Sync & Polish
- [ ] Git sync integration
- [ ] Conflict detection and handling
- [ ] Auto-reindex after sync
- [ ] Termux compatibility testing
- [ ] Interactive mode refinement

### Phase 8: Quality of Life
- [ ] Undo last action
- [ ] Entry editing (open in $EDITOR)
- [ ] Templates for new collections
- [ ] Export (to PDF, HTML)
- [ ] Optional: Obsidian vault compatibility mode

---

## Testing Checklist

### Functional Tests
- [ ] Create new bujo from scratch (empty data dir)
- [ ] Full reindex builds correct SQLite data
- [ ] Add tasks, events, notes to daily log
- [ ] Complete and cancel tasks (file updated correctly)
- [ ] Create monthly log, add calendar events
- [ ] Add items to future log
- [ ] Create collections of each type
- [ ] Run monthly migration
- [ ] Search finds entries across all files
- [ ] Stats calculations are accurate

### Sync Tests
- [ ] Sync between two devices (simulate with two directories)
- [ ] Incremental reindex detects file changes
- [ ] Handle merge conflict gracefully
- [ ] Deleted files are removed from index

### Platform Tests
- [ ] Works in 80-column terminal (Termux)
- [ ] Works with minimal color support
- [ ] SQLite works on Termux
- [ ] Git operations work on both platforms

### Edge Cases
- [ ] Empty files don't crash parser
- [ ] Malformed entries are skipped gracefully
- [ ] Very long entries (>1000 chars)
- [ ] Unicode content (emoji, CJK)
- [ ] 5 years of simulated data (performance test)

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

## Notes for Claude Code

1. **SQLite cache is disposable** — Can always be rebuilt from markdown. Never sync it.
2. **Markdown is authoritative** — If there's ever a mismatch, markdown wins.
3. **Test on both platforms early** — Don't leave Termux compatibility to the end.
4. **FTS5 is powerful** — Use it for search; don't reinvent.
5. **Incremental reindex must be fast** — Hash comparison, not content parsing.
6. **Keep markdown human-editable** — Users will vim their files directly.
7. **Git operations can shell out** — Don't need GitPython if subprocess works.

The goal is a tool that feels as fast and immediate as writing in a notebook, but with the searchability of a database and the sync of git. Prioritize speed of capture above all else.
