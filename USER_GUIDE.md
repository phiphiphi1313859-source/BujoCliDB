# CLIBuJo User Guide

A command-line bullet journal implementing Ryder Carroll's Bullet Journal method. Fast, offline-first, and syncs across devices via git.

---

## Table of Contents

1. [Installation](#installation)
   - [Windows Terminal (WSL)](#windows-terminal-wsl)
   - [Arch Linux (WSL)](#arch-linux-wsl)
   - [Termux (Android)](#termux-android)
2. [Getting Started](#getting-started)
3. [The Symbol Language](#the-symbol-language)
4. [Daily Workflow](#daily-workflow)
5. [Commands Reference](#commands-reference)
6. [Interactive Mode](#interactive-mode)
7. [Syncing Across Devices](#syncing-across-devices)
8. [Monthly Migration](#monthly-migration)
9. [Collections](#collections)
10. [Search and Statistics](#search-and-statistics)
11. [Configuration](#configuration)
12. [Tips and Tricks](#tips-and-tricks)

---

## Installation

### Windows Terminal (WSL)

1. **Install WSL** (if not already installed):
   ```powershell
   wsl --install
   ```

2. **Open your WSL distribution** (Ubuntu, Arch, etc.) in Windows Terminal

3. **Install Python 3.10+**:
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install python3 python3-pip python3-venv git

   # Arch
   sudo pacman -S python python-pip git
   ```

4. **Clone and install CLIBuJo**:
   ```bash
   git clone https://github.com/yourusername/clibujo.git ~/.clibujo-app
   cd ~/.clibujo-app
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

5. **Add to your PATH** (add to `~/.bashrc` or `~/.zshrc`):
   ```bash
   export PATH="$HOME/.clibujo-app/.venv/bin:$PATH"
   ```

6. **Initialize your journal**:
   ```bash
   bujo init
   ```

### Arch Linux (WSL)

1. **Install dependencies**:
   ```bash
   sudo pacman -S python python-pip git
   ```

2. **Clone and install**:
   ```bash
   git clone https://github.com/yourusername/clibujo.git ~/.clibujo-app
   cd ~/.clibujo-app
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

3. **Add to PATH** in `~/.bashrc` or `~/.zshrc`:
   ```bash
   export PATH="$HOME/.clibujo-app/.venv/bin:$PATH"
   ```

4. **Initialize**:
   ```bash
   source ~/.bashrc  # or restart terminal
   bujo init
   ```

### Termux (Android)

1. **Install Termux** from F-Droid (recommended) or Google Play

2. **Setup storage access**:
   ```bash
   termux-setup-storage
   ```

3. **Install dependencies**:
   ```bash
   pkg update && pkg upgrade
   pkg install python git
   ```

4. **Clone and install**:
   ```bash
   git clone https://github.com/yourusername/clibujo.git ~/.clibujo-app
   cd ~/.clibujo-app
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

5. **Add to PATH** in `~/.bashrc`:
   ```bash
   echo 'export PATH="$HOME/.clibujo-app/.venv/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

6. **Initialize**:
   ```bash
   bujo init
   ```

---

## Getting Started

After installation, initialize your bullet journal:

```bash
$ bujo init

Created config: /home/user/.bujo/config.yaml
Initialized git repository

Bullet journal initialized!
  Location: /home/user/.bujo

Run bujo to start journaling.
```

This creates:
- `~/.bujo/` - Your bullet journal home
- `~/.bujo/data/` - All your markdown files (synced via git)
- `~/.bujo/cache.db` - Local SQLite index (never synced)
- `~/.bujo/config.yaml` - Your configuration

---

## The Symbol Language

CLIBuJo uses Ryder Carroll's rapid logging symbols:

### Entry Types

```
[ ]  Task           Something to do
 ○   Event          Date-related entry
 -   Note           Fact, idea, observation
```

### Task States

```
[ ]  Open           Not yet done
[x]  Complete       Done!
[>]  Migrated       Moved to another month/collection
[<]  Scheduled      Moved to Future Log
[~]  Cancelled      No longer relevant
```

### Signifiers (Priority Markers)

```
 *   Priority       Important, do first
 !   Inspiration    Great idea or insight
 ?   Explore        Needs research
```

### Examples

```markdown
# December 2, 2025

* [ ] Call the bank about mortgage         <- Priority task
  [ ] Buy groceries                         <- Regular task
  [x] Submit project proposal               <- Completed
  [>] Review insurance policy →future.md    <- Migrated
  ○   Team meeting at 2pm                   <- Event
  -   Project deadline moved to Friday      <- Note
! -   "Done is better than perfect"         <- Inspiration
```

---

## Daily Workflow

### Morning: Review and Add

```bash
# Start your day - opens interactive mode
$ bujo

CLIBuJo                                    December 02, 2025

═══════════════════════════════════════════════════════════

  (empty day — start logging!)

> a
Type [t]ask [e]vent [n]ote: t
Priority? [y/N]: y
> Review quarterly report

Added: * [ ] Review quarterly report
```

### Throughout the Day: Quick Capture

```bash
# Quick add from command line
$ bujo add "[ ] Email client about proposal"
Added: [ ] Email client about proposal

$ bujo add "○ Dentist appointment 3pm"
Added: ○ Dentist appointment 3pm

$ bujo add "- Project X uses the new API"
Added: - Project X uses the new API
```

### Complete Tasks

```bash
# View today's log
$ bujo day

* [ ] [1] Review quarterly report
  [ ] [2] Email client about proposal
  ○   [3] Dentist appointment 3pm
  -       Project X uses the new API

# Complete task 1
$ bujo complete 1
Complete: Review quarterly report

# Or in interactive mode, just type: x 1
```

### Evening: Sync

```bash
$ bujo sync

Syncing...
  ✓ Pulled 0 changes
  ✓ Committed: "sync: laptop 2025-12-02T18:30:00"
  ✓ Pushed to origin/main

Sync complete!
```

---

## Commands Reference

### Viewing Logs

| Command | Description |
|---------|-------------|
| `bujo` | Interactive mode (default) |
| `bujo day` | View today's daily log |
| `bujo day 2025-12-01` | View specific date |
| `bujo day yesterday` | View yesterday |
| `bujo day -2` | View 2 days ago |
| `bujo week` | View current week summary |
| `bujo month` | View current month |
| `bujo month december` | View specific month |
| `bujo future` | View future log |
| `bujo index` | View master index |

### Adding Entries

```bash
# Auto-detect from prefix
bujo add "[ ] Task text"           # Task
bujo add "* [ ] Priority task"     # Priority task
bujo add "○ Event text"            # Event
bujo add "- Note text"             # Note

# Explicit type
bujo add -t "Task text"            # Task
bujo add -e "Event text"           # Event
bujo add -n "Note text"            # Note
bujo add -t "Urgent" -p            # Priority task

# Add to specific location
bujo add "[ ] Task" -c myproject   # Add to collection
bujo add "[ ] Task" -f "jan"       # Add to future log January
```

### Managing Tasks

```bash
bujo complete 1          # Complete task #1 from today
bujo complete abc123     # Complete by reference ID
bujo cancel 2            # Cancel task #2
bujo migrate 1           # Migrate task (interactive)
bujo migrate 1 future    # Migrate to future log
bujo schedule 1 march    # Schedule to March
bujo undo                # Undo last action
```

### Collections

```bash
bujo collections                        # List all collections
bujo collection myproject               # View collection
bujo collection myproject --new -t project   # Create new
bujo collection myproject -e            # Edit in $EDITOR
```

### Search and Stats

```bash
bujo search "quarterly report"    # Full-text search
bujo tasks                        # List all open tasks
bujo tasks -s complete            # List completed tasks
bujo tasks -c myproject           # Tasks in collection
bujo tasks --from 2025-12-01      # Tasks from date
bujo stats                        # Show statistics
bujo stats -y 2025                # Stats for year
```

### Sync and Maintenance

```bash
bujo sync              # Pull, commit, push
bujo reindex           # Rebuild cache (incremental)
bujo reindex --full    # Full cache rebuild
bujo edit              # Edit today in $EDITOR
bujo edit future       # Edit future log
bujo export -f html    # Export to HTML
bujo export -f pdf     # Export to PDF
```

---

## Interactive Mode

Run `bujo` without arguments to enter interactive mode:

```
CLIBuJo                                    December 02, 2025

═══════════════════════════════════════════════════════════

* [ ] [1] Review quarterly report
  [ ] [2] Email client about proposal
  [x] [3] Submit project proposal
  ○   [4] Dentist appointment 3pm
  -       Project X uses the new API

───────────────────────────────────────────────────────────
[a]dd [x]complete [>]migrate [~]cancel [c]ollection [m]onth [f]uture [/]search [s]ync [e]dit [q]uit

> _
```

### Interactive Commands

| Key | Action |
|-----|--------|
| `a` | Add new entry |
| `x 1` | Complete task 1 |
| `~ 2` | Cancel task 2 |
| `> 3` | Migrate task 3 |
| `c` | List collections |
| `m` | View monthly log |
| `f` | View future log |
| `/` | Search |
| `s` | Sync with git |
| `e` | Edit in $EDITOR |
| `u` | Undo last action |
| `d tomorrow` | Change to different date |
| `?` | Help |
| `q` | Quit |

### Quick Add (type directly)

```
> [ ] New task
Added: [ ] New task

> * [ ] Priority task
Added: * [ ] Priority task

> ○ Meeting at 4pm
Added: ○ Meeting at 4pm

> - Important note
Added: - Important note
```

---

## Syncing Across Devices

CLIBuJo uses git for synchronization. Your markdown files sync; the SQLite cache rebuilds locally.

### Initial Setup (First Device)

```bash
# After bujo init, set up remote
cd ~/.bujo
git remote add origin git@github.com:yourusername/bujo-data.git
git push -u origin main
```

### Setup on Additional Devices

```bash
# Clone your existing journal
git clone git@github.com:yourusername/bujo-data.git ~/.bujo

# Install CLIBuJo (see Installation section)
# ...

# The cache will rebuild automatically on first run
bujo
Reindexed 47 file(s)
```

### Daily Sync Workflow

```bash
# Start of session (pulls changes)
$ bujo
Reindexed 3 file(s)

# ... do your work ...

# End of session (commits and pushes)
$ bujo sync
Syncing...
  ✓ Pulled 0 changes
  ✓ Committed: "sync: phone 2025-12-02T18:30:00"
  ✓ Pushed to origin/main
```

### Auto-Pull on Startup

By default, CLIBuJo pulls on startup. Configure in `~/.bujo/config.yaml`:

```yaml
sync:
  enabled: true
  remote: origin
  branch: main
  auto_pull: true    # Pull when starting bujo
  auto_push: false   # Require explicit 'bujo sync'
```

### Handling Conflicts

If you edit the same entry on two devices:

```bash
$ bujo sync
Conflicts detected in 1 file(s):
  - daily/2025-12-02.md

Resolve conflicts manually, then run 'bujo sync' again.
```

Open the file and resolve:

```markdown
<<<<<<< HEAD
[ ] My version of the task
=======
[x] Their version of the task
>>>>>>> origin/main
```

Choose the correct version, remove conflict markers, save, then:

```bash
$ bujo sync
```

---

## Monthly Migration

At the start of each month, review incomplete tasks from the previous month:

```bash
$ bujo migration

Monthly Migration: November 2025 → December 2025

Reviewing 12 incomplete tasks...

[1/12] [ ] Fix bug in API endpoint
       Source: daily/2025-11-15.md
       Age: 17 days

       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: k

       → Migrated to December 2025

[2/12] [ ] Learn Rust
       Source: daily/2025-11-08.md
       Age: 24 days

       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: f

       Which month? (1-12, or 'someday'): someday

       → Scheduled to Someday

[3/12] [ ] Buy birthday gift for Dave
       Source: daily/2025-11-22.md
       Age: 10 days

       [k]eep  [d]rop  [f]uture  [c]ollection  [s]kip: d

       → Dropped

...

Migration complete!
  Kept:       8
  Future:     2
  Collection: 1
  Dropped:    1
```

### Migration Options

| Key | Action |
|-----|--------|
| `k` | Keep - migrate to current month |
| `d` | Drop - mark as cancelled |
| `f` | Future - schedule to future log |
| `c` | Collection - move to a collection |
| `s` | Skip - decide later |

---

## Collections

Collections are themed lists for projects, trackers, or reference material.

### Creating Collections

```bash
# Create a project collection
$ bujo collection myproject --new --type project
Created collection: myproject (project)

# Create a tracker
$ bujo collection habits --new --type tracker

# Create a simple list
$ bujo collection books --new --type list
```

### Collection Types

**Project** - Goals, tasks, and notes:
```markdown
# My Project

> Project description

## Goals

- Complete MVP by Q1
- Get 100 beta users

## Tasks

[ ] Design user interface
[ ] Build API endpoints
[x] Set up database

## Notes

- Consider using Redis for caching
```

**Tracker** - Logging over time:
```markdown
# Habit Tracker

> Daily habits

## Log

2025-12-01: ✓ Exercise, ✓ Reading, ✗ Meditation
2025-12-02: ✓ Exercise, ✓ Reading, ✓ Meditation
```

**List** - Simple reference:
```markdown
# Books to Read

> Reading list

- The Pragmatic Programmer
- Clean Code
- Designing Data-Intensive Applications
```

### Adding to Collections

```bash
# Add task to collection
$ bujo add "[ ] Design login page" -c myproject
Added: [ ] Design login page

# Or migrate an existing task
$ bujo migrate 3
Migrating: Design database schema

Destination:
  [m] Next month
  [f] Future log
  [c] Collection

> c
Collection name: myproject

→ Moved to myproject
```

---

## Search and Statistics

### Full-Text Search

```bash
$ bujo search "database"

Found 5 result(s):

[1] 2025-12-02 daily    [ ] Design database schema
[2] 2025-11-28 daily    [x] Research database options
[3] myproject collection [ ] Set up database migrations
[4] myproject collection -  PostgreSQL supports JSONB
[5] 2025-11-15 daily    ○  Database design meeting

[number] to jump, [Enter] to return: 3

Opening collections/projects/myproject.md in $EDITOR...
```

### Filtering Tasks

```bash
# All open tasks
$ bujo tasks

# Completed tasks
$ bujo tasks --status complete

# Priority tasks only
$ bujo tasks --priority

# Tasks in a collection
$ bujo tasks --collection myproject

# Tasks from date range
$ bujo tasks --from 2025-12-01 --to 2025-12-31
```

### Statistics

```bash
$ bujo stats

CLIBuJo Stats: 2025

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
Jan 25     67    52   78%
Feb 25     71    55   77%
Mar 25     83    61   73%
...
Dec 25     23    12   52%  (in progress)

Most Active Collections
──────────────────────────────────────
myproject:      47 tasks (31 complete)
work:           34 tasks (28 complete)
home:           22 tasks (19 complete)
```

---

## Configuration

Edit `~/.bujo/config.yaml`:

```yaml
# CLIBuJo Configuration

# Editor for full-page editing
editor: vim

# Date format
date_format: "%B %d, %Y"  # December 02, 2025
short_date: "%b %d"       # Dec 02

# First day of week (0=Monday, 6=Sunday)
week_start: 0

# Display
narrow_threshold: 60      # Compact mode below this width
show_entry_refs: false    # Show [abc123] refs or [1] indices

# Sync settings
sync:
  enabled: true
  remote: origin
  branch: main
  auto_pull: true         # Pull on startup
  auto_push: false        # Require explicit sync

# Index settings
index:
  auto_reindex: true      # Reindex on startup
  reindex_on_sync: true   # Reindex after pull

# Collection types
collection_types:
  - project
  - tracker
  - list

# Custom signifiers (extend defaults: * ! ?)
# signifiers:
#   "@": "waiting"
#   "#": "delegated"
```

### Environment Variables

```bash
# Use a different bujo location
export BUJO_DIR=/path/to/my/bujo

# Set your editor
export EDITOR=nvim
```

---

## Tips and Tricks

### 1. Shell Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias b='bujo'
alias ba='bujo add'
alias bd='bujo day'
alias bs='bujo sync'
alias bx='bujo complete'
```

### 2. Quick Task Entry

```bash
# One-liner with priority
bujo add "* [ ] Urgent: call client NOW"

# Add event for today
bujo add "○ Lunch with Sarah 12:30"
```

### 3. Review Yesterday

```bash
bujo day yesterday
```

### 4. Plan Your Week

```bash
bujo week
```

### 5. Export for Sharing

```bash
# Export current month to HTML
bujo export -f html -m 12 -o december-2025.html

# Export full year to PDF (requires weasyprint)
pip install 'clibujo[export]'
bujo export -f pdf -y 2025 -o year-2025.pdf
```

### 6. Edit Directly

Your files are plain markdown. Edit them directly:

```bash
vim ~/.bujo/data/daily/2025-12-02.md
```

CLIBuJo will detect changes and reindex automatically.

### 7. Backup Strategy

Your git history IS your backup. But for extra safety:

```bash
# Create a tarball backup
tar -czf bujo-backup-$(date +%Y%m%d).tar.gz ~/.bujo/data
```

### 8. Termux Widget

Create a Termux widget for quick capture:

```bash
# ~/.shortcuts/bujo-add
#!/bin/bash
source ~/.clibujo-app/.venv/bin/activate
bujo add "$@"
```

### 9. View in Any Markdown App

Your files work in any markdown viewer:
- VS Code
- Typora
- iA Writer
- GitHub

### 10. The Philosophy

Remember: **The friction is the feature.**

Migration isn't automatic because reviewing tasks makes you decide:
- Is this still relevant?
- Why haven't I done this?
- Should I actually do this, or let it go?

This intentional review is what makes bullet journaling effective.

---

## File Structure

```
~/.bujo/
├── config.yaml              # Configuration
├── cache.db                 # SQLite cache (local only)
├── .git/                    # Git repository
├── .gitignore               # Ignores cache.db
└── data/
    ├── index.md             # Auto-generated index
    ├── future.md            # Future log
    ├── daily/
    │   ├── 2025-12-01.md
    │   ├── 2025-12-02.md
    │   └── ...
    ├── months/
    │   ├── 2025-12.md
    │   └── ...
    └── collections/
        ├── projects/
        │   └── myproject.md
        ├── trackers/
        │   └── habits.md
        └── lists/
            └── books.md
```

---

## Getting Help

```bash
# General help
bujo --help

# Command-specific help
bujo add --help
bujo migrate --help

# In interactive mode
> ?
```

---

## Credits

CLIBuJo implements [Ryder Carroll's Bullet Journal Method](https://bulletjournal.com/).

The goal is a tool that feels as fast as writing in a notebook, with the searchability of a database and the sync of git.

**Prioritize speed of capture above all else.**
