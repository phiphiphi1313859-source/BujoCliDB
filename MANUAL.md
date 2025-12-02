# CLIBuJo User Manual
## Command-Line Bullet Journal v2.0

**A Complete Guide for Windows, macOS, Linux, WSL, and Termux**

---

```
   _____ _      _____ ____        _
  / ____| |    |_   _|  _ \      | |
 | |    | |      | | | |_) |_   _| | ___
 | |    | |      | | |  _ <| | | | |/ _ \
 | |____| |____ _| |_| |_) | |_| | | (_) |
  \_____|______|_____|____/ \__,_| |\___/
                               _/ |
                              |__/
```

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
   - [Windows Terminal](#21-windows-terminal)
   - [macOS](#22-macos)
   - [WSL (Arch Linux)](#23-wsl-arch-linux)
   - [Termux (Android)](#24-termux-android)
3. [Getting Started](#3-getting-started)
4. [The Daily Log](#4-the-daily-log)
5. [Tasks, Events, and Notes](#5-tasks-events-and-notes)
6. [Signifiers (Priority Markers)](#6-signifiers-priority-markers)
7. [Collections](#7-collections)
8. [Habit Tracking](#8-habit-tracking)
9. [Migration](#9-migration)
10. [Mood Tracking](#10-mood-tracking)
11. [Syncing Across Devices](#11-syncing-across-devices)
12. [Exporting to PDF](#12-exporting-to-pdf)
13. [Interactive Mode](#13-interactive-mode)
14. [Undo Operations](#14-undo-operations)
15. [Command Reference](#15-command-reference)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Introduction

### What is CLIBuJo?

CLIBuJo (Command-Line Bullet Journal) is a digital implementation of Ryder Carroll's Bullet Journal method, designed to work entirely from your terminal. It combines the simplicity and intentionality of analog journaling with the power and convenience of digital tools.

### What is the Bullet Journal Method?

The Bullet Journal is an organizational system that uses:

- **Rapid Logging**: Quick capture of tasks, events, and notes
- **Migration**: Regularly reviewing and moving tasks forward
- **Collections**: Grouping related items together
- **Signifiers**: Priority markers for important items

CLIBuJo extends this with:

- **Habit Tracking**: Monitor recurring behaviors
- **Mood Tracking**: Track mental health metrics
- **Cloud Sync**: Keep multiple devices in sync
- **PDF Export**: Create printable reports

### Why Use a Terminal?

- **Speed**: No mouse needed, just type
- **Focus**: No distracting interfaces
- **Portability**: Works over SSH, on any computer
- **Integration**: Combine with other command-line tools

---

## 2. Installation

### 2.1 Windows Terminal

**Prerequisites**: Python 3.10 or newer

**Step 1: Install Python**

1. Download Python from https://www.python.org/downloads/
2. During installation, CHECK "Add Python to PATH"
3. Click "Install Now"

**Step 2: Open Windows Terminal**

Press `Win + X`, then click "Terminal" (or "Windows Terminal")

**Step 3: Install CLIBuJo**

```powershell
pip install clibujo
```

**Step 4: Initialize the database**

```powershell
bujo init
```

**What you should see:**

```
Database initialized.
```

**Step 5: Verify installation**

```powershell
bujo --version
```

**Output:**

```
CLIBuJo v2.0.0
```

---

### 2.2 macOS

**Step 1: Open Terminal**

Press `Cmd + Space`, type "Terminal", press Enter

**Step 2: Install Python (if needed)**

macOS comes with Python, but you may need a newer version:

```bash
# Install Homebrew first (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python
```

**Step 3: Install CLIBuJo**

```bash
pip3 install clibujo
```

**Step 4: Initialize**

```bash
bujo init
```

**Step 5: Add to PATH (if needed)**

If you get "command not found", add this to your `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then restart Terminal or run:

```bash
source ~/.zshrc
```

---

### 2.3 WSL (Arch Linux)

**Step 1: Open WSL Terminal**

Press `Win + R`, type `wsl`, press Enter

**Step 2: Update system and install Python**

```bash
sudo pacman -Syu
sudo pacman -S python python-pip
```

**Step 3: Create a virtual environment (recommended)**

```bash
python -m venv ~/bujo-env
source ~/bujo-env/bin/activate
```

**Step 4: Install CLIBuJo**

```bash
pip install clibujo
```

**Step 5: Initialize**

```bash
bujo init
```

**Make it permanent**: Add this to your `~/.bashrc`:

```bash
source ~/bujo-env/bin/activate
```

---

### 2.4 Termux (Android)

**Step 1: Install Termux**

Download from F-Droid (NOT Google Play, which has an outdated version):
https://f-droid.org/packages/com.termux/

**Step 2: Update packages**

```bash
pkg update && pkg upgrade
```

**Step 3: Install Python**

```bash
pkg install python
```

**Step 4: Install CLIBuJo**

```bash
pip install clibujo
```

**Step 5: Initialize**

```bash
bujo init
```

**Storage access** (if you want to export files):

```bash
termux-setup-storage
```

---

## 3. Getting Started

### Your First Day

After installation, let's set up your bullet journal:

**Step 1: View today's log (empty at first)**

```bash
bujo
```

**What you see:**

```
===============================
Tuesday, December 02, 2025
===============================

(No entries)
```

**Step 2: Add your first task**

```bash
bujo add "Learn CLIBuJo"
```

**Output:**

```
Added: [1] [ ] Learn CLIBuJo
```

**Step 3: View today again**

```bash
bujo
```

**Now you see:**

```
===============================
Tuesday, December 02, 2025
===============================

TASKS
  [1] [ ] Learn CLIBuJo
```

**Step 4: Mark it done!**

```bash
bujo done 1
```

**Output:**

```
Completed: [1] [x] Learn CLIBuJo
```

---

### Understanding the Display

Here's what each part means:

```
[1] * [ ] Important meeting prep
 ^  ^  ^   ^
 |  |  |   +-- The task description
 |  |  +------ Status: [ ] open, [x] done, [>] migrated
 |  +--------- Signifier: * means priority
 +------------ Entry ID (use this number in commands)
```

---

## 4. The Daily Log

The daily log is your home base. It shows everything happening today.

### Viewing Today

```bash
bujo
```

Or explicitly:

```bash
bujo today
```

### Viewing Other Days

```bash
bujo view yesterday        # Yesterday
bujo view tomorrow         # Tomorrow
bujo view -3              # 3 days ago
bujo view +5              # 5 days from now
bujo view 2025-12-25      # Specific date
```

### Example Daily Log

```
===============================
Tuesday, December 02, 2025
===============================

EVENTS
  [1] o Team standup at 9am
  [2] o Dentist at 2pm

TASKS
  [3] * [ ] Finish quarterly report
  [4]   [ ] Review pull requests
  [5]   [x] Email client

NOTES
  [6] - New API endpoint available

HABITS
  [x] Morning meditation (daily) (7 streak)
  [ ] Exercise (daily)
  [x] Read 20 pages (daily)
```

**Legend:**
- `o` = Event
- `[ ]` = Open task
- `[x]` = Completed task
- `-` = Note
- `*` = Priority signifier

---

## 5. Tasks, Events, and Notes

### Three Types of Entries

| Type | Symbol | Purpose | Has Status? |
|------|--------|---------|-------------|
| Task | `[ ]` | Something you need to do | Yes |
| Event | `o` | Something happening at a time | No |
| Note | `-` | Information to remember | No |

### Adding Entries

**Tasks (default):**

```bash
bujo add "Buy groceries"
bujo add "Call mom" -d tomorrow
```

**Events:**

```bash
bujo add "Team meeting at 2pm" -t event
bujo add "Doctor appointment" -t event -d 2025-12-15
```

**Notes:**

```bash
bujo add "Project deadline moved to January" -t note
bujo add "Password: check vault" -t note
```

### Task Statuses

Tasks move through these statuses:

```
[ ] Open      - Not yet started
[x] Complete  - Done!
[>] Migrated  - Moved to another date
[<] Scheduled - Planned for future
[~] Cancelled - No longer needed
```

### Completing and Cancelling

```bash
bujo done 3              # Mark task #3 complete
bujo entries complete 3  # Same thing, longer form
bujo entries cancel 4    # Cancel task #4
bujo entries reopen 3    # Reopen a completed task
```

### Editing and Deleting

```bash
bujo entries edit 3 "Updated task text"
bujo entries delete 5
bujo entries delete 5 -y  # Skip confirmation
```

---

## 6. Signifiers (Priority Markers)

Signifiers are symbols that give extra meaning to entries.

### Available Signifiers

| Symbol | Name | Meaning |
|--------|------|---------|
| `*` | Priority | Do this first! |
| `!` | Inspiration | Great idea |
| `?` | Explore | Needs research |
| `@` | Waiting | Blocked on someone |
| `#` | Delegated | Assigned to others |

### Adding Signifiers

**Method 1: Prefix in text**

```bash
bujo add "*Important deadline"
bujo add "!Great idea for the project"
bujo add "?How does this API work"
bujo add "@Waiting for client approval"
bujo add "#Assigned to marketing team"
```

**Method 2: Using the flag**

```bash
bujo add "Important deadline" -p    # Sets priority
```

**Method 3: Edit existing**

```bash
bujo entries edit 3 -s priority
bujo entries edit 3 -s inspiration
```

### How They Look

```
TASKS
  [1] * [ ] Priority task (do first!)
  [2] ! [ ] Inspiration (great idea)
  [3] ? [ ] Explore (needs research)
  [4] @ [ ] Waiting (blocked)
  [5] # [ ] Delegated (assigned out)
  [6]   [ ] Regular task
```

---

## 7. Collections

Collections group related entries together, like folders for your tasks.

### Three Types of Collections

| Type | Purpose | Example |
|------|---------|---------|
| Project | Tracked work with progress | "Website Redesign" |
| Tracker | List of items to track | "Books to Read" |
| List | Simple checklist | "Groceries" |

### Creating Collections

```bash
bujo collections create "Q4 Goals" -t project
bujo collections create "Reading List" -t tracker
bujo collections create "Shopping" -t list
```

### Viewing Collections

**List all:**

```bash
bujo collections list
```

**Output:**

```
PROJECTS
  [1] Q4 Goals (2/5 complete)
  [2] Website Redesign (75%)

TRACKERS
  [3] Reading List (12 items)

LISTS
  [4] Shopping (3 items)
```

**View one collection:**

```bash
bujo collections view "Q4 Goals"
```

**Output:**

```
===============================
PROJECT: Q4 Goals
===============================

Progress: 2/5 tasks (40%)

  [10] [x] Define quarterly objectives
  [11] [x] Set up tracking system
  [12] [ ] Review with team
  [13] [ ] Finalize budget
  [14] [ ] Launch marketing campaign
```

### Adding to Collections

```bash
bujo add "Design homepage" -c "Website Redesign"
bujo add "Read 'Atomic Habits'" -c "Reading List"
```

### Managing Collections

```bash
bujo collections edit 1 -n "Q4 2025 Goals"     # Rename
bujo collections archive "Old Project"          # Hide from list
bujo collections unarchive "Old Project"        # Show again
bujo collections delete "Shopping" --keep-entries  # Delete but keep tasks
```

---

## 8. Habit Tracking

Track recurring behaviors and build streaks.

### Creating Habits

**Daily habits:**

```bash
bujo habits add "Morning meditation" -f daily
bujo habits add "Exercise" -f daily -c wellness
```

**Weekly habits:**

```bash
bujo habits add "Weekly review" -f weekly
bujo habits add "Gym" -f weekly:3    # 3 times per week
```

**Specific days:**

```bash
bujo habits add "Team standup" -f days:mon,tue,wed,thu,fri
```

**Monthly habits:**

```bash
bujo habits add "Budget review" -f monthly
bujo habits add "Call parents" -f monthly:2   # Twice a month
```

### Marking Habits Done

```bash
bujo habits done "Morning meditation"
bujo done "Morning meditation"           # Shortcut
bujo habits done "Exercise" -n "30 min run"  # With note
```

### Viewing Habits

**Today's habits:**

```bash
bujo habits today
```

**Output:**

```
== HABITS DUE TODAY ==

WELLNESS
  [x] Morning meditation (daily) (7 streak)
  [ ] Exercise (daily)

LEARNING
  [ ] Read 20 pages (daily)
```

**All habits:**

```bash
bujo habits list
```

**Individual habit:**

```bash
bujo habits status "Exercise"
```

**Monthly calendar:**

```bash
bujo habits calendar "Exercise"
```

**Output:**

```
== Exercise: December 2025 ==

 Mo Tu We Th Fr Sa Su
  1  2  3  4  5  6  7
  X  X  .  X  X  .  X
  8  9 10 11 12 13 14
  X  X  X  X  X  .  X
 15 16 17 18 19 20 21
  X  X  X  .  X  X  X
 22 23 24 25 26 27 28
  X  X  X  X  X  .  X
 29 30 31
  X  X

Completed: 26/31 days (84%)
Current streak: 3 days
```

### Managing Habits

```bash
bujo habits pause "Gym"        # Temporarily stop tracking
bujo habits resume "Gym"       # Start again
bujo habits quit "Smoking"     # Mark as intentionally stopped
bujo habits delete "Old habit" # Remove completely
```

---

## 9. Migration

Migration is a key Bullet Journal practice: reviewing old tasks and deciding what to do with them.

### The Migration Review

At the end of each week (or whenever you like), review old open tasks:

```bash
bujo migrate review
```

**Output:**

```
== Open Tasks Before Today ==

2025-11-28:
  [15] [ ] Call insurance company
  [16] [ ] Update resume

2025-11-30:
  [20] [ ] Review project proposal

Total: 3 task(s) may need migration

Use 'bujo migrate forward <id>' to migrate individual tasks
Or 'bujo migrate bulk' to migrate all to today
```

### Migrating Tasks

**Move one task to today:**

```bash
bujo migrate forward 15
```

**Move to a specific date:**

```bash
bujo migrate to-date 16 2025-12-15
```

**Move to monthly log (future month):**

```bash
bujo migrate to-month 20 2026-01
```

**Move to a collection:**

```bash
bujo migrate to-collection 15 "Phone Calls"
```

**Bulk migrate all:**

```bash
bujo migrate bulk
```

**Output:**

```
Migrate 3 task(s) to today? [y/N]: y

Migrated 3 task(s) to today:
  [21] [ ] Call insurance company
  [22] [ ] Update resume
  [23] [ ] Review project proposal
```

### View Migration History

See where a task has been:

```bash
bujo migrate history 21
```

**Output:**

```
== Migration History for #21 ==

Current: [21] [ ] Call insurance company

  2025-12-02: 2025-11-28 -> 2025-12-02
  2025-11-28: 2025-11-20 -> 2025-11-28
```

---

## 10. Mood Tracking

Track your mental health with comprehensive mood logging.

### Quick Daily Entry

The fastest way to log:

```bash
bujo mood quick 2 7 7.5
```

This logs:
- Mood: +2 (scale: -5 to +5)
- Energy: 7 (scale: 1-10)
- Sleep: 7.5 hours

### Full Daily Entry

For more detail:

```bash
bujo mood log
```

**Interactive prompts:**

```
Logging for 2025-12-02

Mood (-5 to +5): 2
Energy (1-10): 7
Sleep hours: 7.5
Sleep quality (1-5): 4
Irritability (0-5): 1
Anxiety (0-5): 2
Note (optional): Good productive day

[x] Logged for 2025-12-02
```

### Adding Extra Dimensions

```bash
bujo mood add racing:2 concentration:4 social:3
```

**Available dimensions:**

| Dimension | Range | What it measures |
|-----------|-------|------------------|
| mood | -5 to +5 | Overall mood |
| energy | 1-10 | Energy level |
| sleep | hours | Hours slept |
| sleep_quality | 1-5 | Quality of sleep |
| irritability | 0-5 | Irritability |
| anxiety | 0-5 | Anxiety level |
| racing | 0-5 | Racing thoughts |
| impulsivity | 0-5 | Impulsive urges |
| concentration | 0-5 | Ability to focus |
| social | 0-5 | Social drive |
| appetite | 0-5 | Appetite level |

### Viewing Mood Data

**Today:**

```bash
bujo mood today
```

**Output:**

```
December 02, 2025 (Tuesday)
==================================================

LOGGED
  Mood:        +2  ##########----------
  Energy:       7  ##############------
  Irritability: 1  ####----------------

SLEEP
  Duration:   7.5 hrs
  Quality:    4/5

NOTE
  "Good productive day"
```

**Week view:**

```bash
bujo mood week
```

**Output:**

```
Week of Dec 02 - Dec 08, 2025
==================================================

        Mon   Tue   Wed   Thu   Fri   Sat   Sun     Avg
------------------------------------------------------------------------
Mood     +1    +2    +1    +2    +3     .     -    +1.8
Energy    6     7     6     7     8     .     -     6.8
Sleep   7.0   7.5   6.5   7.5   8.0     .     -     7.3
Irritab   2     1     2     1     0     .     -     1.2

. = not logged   - = future
```

**Long-term trends:**

```bash
bujo mood trend --months 6
```

### Medication Tracking

**Add medications:**

```bash
bujo mood meds add "Sertraline" --dose "100mg" --time morning
bujo mood meds add "Melatonin" --dose "3mg" --time night
```

**Log medications taken:**

```bash
bujo mood meds log              # Show today's status
bujo mood meds log Sertraline   # Mark as taken
bujo mood meds log Melatonin --missed  # Mark as missed
```

**Output:**

```
[x] Sertraline (morning)
[ ] Melatonin (night)
```

### Episode Tracking

Track mood episodes (depression, hypomania, mania, mixed):

**Start an episode:**

```bash
bujo mood episode start -t depression -s 3
```

**End when it's over:**

```bash
bujo mood episode end -n "Feeling better after therapy adjustment"
```

**View history:**

```bash
bujo mood episode list
```

**Output:**

```
Episodes (last 12 months)

  2025-11-01 to 2025-11-15 (15 days)
    Depression Severity: 3/5
    "Triggered by work stress"

  2025-08-10 to 2025-08-17 (8 days)
    Hypomania Severity: 2/5
```

### Custom Triggers

Set up warnings for concerning patterns:

```bash
bujo mood trigger add "sleep < 5.5 for 2 days" --warn "Sleep critically low!"
bujo mood trigger add "energy > 8 and sleep < 6" --warn "Possible hypomania pattern"
```

**Check patterns:**

```bash
bujo mood patterns
```

### Baselines and Targets

**Set targets:**

```bash
bujo mood target set sleep 8
bujo mood target set steps 10000
```

**Calculate your baseline:**

```bash
bujo mood baseline recalculate
```

**View baseline:**

```bash
bujo mood baseline show
```

**Output:**

```
Your Baselines

  mood          1.5 (std = 2.1)
  Normal range: -0.6 to 3.6

  energy        6.8 (std = 1.2)
  Normal range: 5.6 to 8.0

  sleep         7.2 (std = 0.8)
  Normal range: 6.4 to 8.0

(Based on 90 days of data)
```

---

## 11. Syncing Across Devices

Sync your journal between devices using rclone (supports Google Drive, Dropbox, OneDrive, etc.).

### Step 1: Install rclone

**Windows:**

```powershell
winget install Rclone.Rclone
```

**macOS:**

```bash
brew install rclone
```

**Linux/WSL:**

```bash
sudo pacman -S rclone      # Arch
sudo apt install rclone    # Debian/Ubuntu
```

**Termux:**

```bash
pkg install rclone
```

### Step 2: Configure rclone

```bash
rclone config
```

Follow the prompts to add your cloud storage. Example for Google Drive:

1. Type `n` for new remote
2. Name it `gdrive`
3. Choose "Google Drive"
4. Follow the authentication steps

### Step 3: Set Up CLIBuJo Sync

**Set your remote:**

```bash
export BUJO_SYNC_REMOTE="gdrive:bujo"
```

Make it permanent by adding to your shell config:

```bash
# Add to ~/.bashrc, ~/.zshrc, or equivalent
echo 'export BUJO_SYNC_REMOTE="gdrive:bujo"' >> ~/.bashrc
```

### Step 4: Sync!

**Push your journal to the cloud:**

```bash
bujo sync push
```

**Pull from the cloud:**

```bash
bujo sync pull
```

**Auto-sync (push if local newer, pull if remote newer):**

```bash
bujo sync auto
```

**Check status:**

```bash
bujo sync status
```

**Output:**

```
== Sync Status ==

rclone: installed
Remote: gdrive:bujo

Local modified:  2025-12-02 18:30:15
Remote modified: 2025-12-02 14:20:00

Status: Local is newer (push to sync)
```

### Syncing Workflow

**Morning (at work):**

```bash
bujo sync pull    # Get latest from home
bujo              # Start your day
```

**Evening (going home):**

```bash
bujo sync push    # Save to cloud
```

**At home:**

```bash
bujo sync pull    # Get work updates
```

### Backups

The sync system automatically creates backups:

```bash
bujo sync backups          # List backups
bujo sync backup           # Create manual backup
bujo sync restore backup_2025-12-02.db  # Restore
```

---

## 12. Exporting to PDF

Create printable PDF reports of your journal.

### Export Commands

**Today:**

```bash
bujo export today
```

**Specific date:**

```bash
bujo export date 2025-12-01
```

**This week:**

```bash
bujo export week
```

**Last week:**

```bash
bujo export week -w -1
```

**This month:**

```bash
bujo export month
```

**Specific month:**

```bash
bujo export month 2025-11
```

**Date range:**

```bash
bujo export range 2025-12-01 2025-12-15
```

**A collection:**

```bash
bujo export collection "Q4 Goals"
```

**Habit report:**

```bash
bujo export habits 2025-12
```

### Custom Output Path

```bash
bujo export month -o ~/Documents/december_journal.pdf
```

### Installing PDF Support

If you get an error about fpdf2:

```bash
pip install clibujo[export]
```

---

## 13. Interactive Mode

For rapid-fire journaling, use interactive mode:

```bash
bujo interactive
```

### Interactive Commands

| Type This | What It Does |
|-----------|--------------|
| `text` | Add a task |
| `e text` | Add an event |
| `n text` | Add a note |
| `x 1` | Complete task #1 |
| `~ 1` | Cancel task #1 |
| `o 1` | Reopen task #1 |
| `d 1` | Delete entry #1 |
| `h Exercise` | Mark habit done |
| `> 5` | Migrate task to today |
| `t` | View today |
| `y` | View yesterday |
| `+3` | View 3 days ahead |
| `-2` | View 2 days ago |
| `s query` | Search |
| `u` | Undo last action |
| `?` | Show help |
| `q` | Quit |

### Interactive Session Example

```
[2025-12-02] > Buy groceries
Added: [1] [ ] Buy groceries

[2025-12-02] > *Call the bank
Added: [2] * [ ] Call the bank

[2025-12-02] > e Team meeting at 2pm
Added: [3] o Team meeting at 2pm

[2025-12-02] > h Morning meditation
Marked done: Morning meditation (8 streak)

[2025-12-02] > x 1
Completed: [1] [x] Buy groceries

[2025-12-02] > t
===============================
Tuesday, December 02, 2025
===============================

EVENTS
  [3] o Team meeting at 2pm

TASKS
  [2] * [ ] Call the bank
  [1]   [x] Buy groceries

HABITS
  [x] Morning meditation (daily) (8 streak)

[2025-12-02] > q
Goodbye!
```

---

## 14. Undo Operations

Made a mistake? Undo it!

### Quick Undo

```bash
bujo undo
```

This undoes your last action.

### Undo Multiple

```bash
bujo undo multiple 3   # Undo last 3 actions
```

### View Undo History

```bash
bujo undo-history
```

**Output:**

```
Recent actions:
  1. Completed entry #5: "Review report"
  2. Created entry #6: "New task"
  3. Updated entry #4
  4. Mark habit done: "Morning walk"
  5. Deleted entry #3
```

### What Can Be Undone?

- Creating/editing/deleting entries
- Completing/cancelling/reopening tasks
- Creating/editing habits
- Marking habits done
- Creating/editing/deleting collections
- Migrating tasks

---

## 15. Command Reference

### Top-Level Commands

| Command | Description |
|---------|-------------|
| `bujo` | View today's log |
| `bujo add TEXT` | Quick add task |
| `bujo done ID` | Complete task or habit |
| `bujo view DATE` | View a day's log |
| `bujo search QUERY` | Search entries |
| `bujo undo` | Undo last action |
| `bujo init` | Initialize database |
| `bujo interactive` | Start interactive mode |
| `bujo --version` | Show version |

### Entry Commands (`bujo entries ...`)

| Command | Description |
|---------|-------------|
| `entries view DATE` | View a day |
| `entries add TEXT` | Add entry |
| `entries complete ID` | Complete task |
| `entries cancel ID` | Cancel task |
| `entries reopen ID` | Reopen task |
| `entries edit ID TEXT` | Edit entry |
| `entries delete ID` | Delete entry |
| `entries search QUERY` | Search |
| `entries open` | List open tasks |
| `entries week` | View week |
| `entries month` | View month |

### Collection Commands (`bujo collections ...`)

| Command | Description |
|---------|-------------|
| `collections list` | List all |
| `collections view NAME` | View one |
| `collections create NAME` | Create |
| `collections edit NAME` | Edit |
| `collections archive NAME` | Archive |
| `collections delete NAME` | Delete |

### Habit Commands (`bujo habits ...`)

| Command | Description |
|---------|-------------|
| `habits list` | List all |
| `habits add NAME` | Create habit |
| `habits done NAME` | Mark done |
| `habits undo NAME` | Remove completion |
| `habits status NAME` | Show details |
| `habits calendar NAME` | Show calendar |
| `habits today` | Due today |
| `habits pause NAME` | Pause tracking |
| `habits resume NAME` | Resume |
| `habits delete NAME` | Delete |

### Migration Commands (`bujo migrate ...`)

| Command | Description |
|---------|-------------|
| `migrate review` | Show old tasks |
| `migrate forward ID` | Move to today |
| `migrate to-date ID DATE` | Move to date |
| `migrate to-month ID MONTH` | Move to month |
| `migrate to-collection ID NAME` | Move to collection |
| `migrate bulk` | Move all old tasks |
| `migrate history ID` | Show history |

### Mood Commands (`bujo mood ...`)

| Command | Description |
|---------|-------------|
| `mood log` | Full daily entry |
| `mood quick M E S` | Quick entry |
| `mood add DIM:VAL` | Add dimensions |
| `mood today` | View today |
| `mood week` | View week |
| `mood trend` | Long-term view |
| `mood meds add NAME` | Add medication |
| `mood meds log NAME` | Log taken |
| `mood episode start` | Start episode |
| `mood episode end` | End episode |
| `mood trigger add COND` | Add trigger |
| `mood patterns` | Check patterns |
| `mood baseline show` | Show baseline |

### Sync Commands (`bujo sync ...`)

| Command | Description |
|---------|-------------|
| `sync push` | Upload to cloud |
| `sync pull` | Download from cloud |
| `sync auto` | Smart sync |
| `sync status` | Show status |
| `sync backups` | List backups |
| `sync restore NAME` | Restore backup |

### Export Commands (`bujo export ...`)

| Command | Description |
|---------|-------------|
| `export today` | Export today |
| `export date DATE` | Export a date |
| `export week` | Export week |
| `export month MONTH` | Export month |
| `export range START END` | Export range |
| `export collection NAME` | Export collection |
| `export habits MONTH` | Export habit report |

---

## 16. Troubleshooting

### "Command not found: bujo"

**Solution:** Add Python's bin directory to your PATH:

```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"

# Windows (PowerShell)
$env:PATH += ";$env:APPDATA\Python\Python310\Scripts"
```

### "ModuleNotFoundError: No module named 'click'"

**Solution:** Reinstall CLIBuJo:

```bash
pip uninstall clibujo
pip install clibujo
```

### "Database is locked"

**Solution:** Another process is using the database. Close other terminals or wait.

### "rclone: command not found"

**Solution:** Install rclone (see Section 11).

### "PDF export failed"

**Solution:** Install the export dependencies:

```bash
pip install clibujo[export]
```

### Data Location

Your data is stored at:

- **Linux/macOS:** `~/.local/share/bujo/bujo.db`
- **Windows:** `C:\Users\USERNAME\.local\share\bujo\bujo.db`

To use a custom location:

```bash
export BUJO_DIR=/path/to/custom/location
```

### Getting Help

Each command has built-in help:

```bash
bujo --help
bujo entries --help
bujo habits add --help
```

---

## Quick Start Cheat Sheet

```
# VIEW
bujo                    View today
bujo view yesterday     View yesterday

# ADD
bujo add "Task"         Add task
bujo add "Event" -t event    Add event
bujo add "*Priority"    Add priority task

# COMPLETE
bujo done 1             Complete task #1
bujo done "Exercise"    Complete habit

# HABITS
bujo habits add "X" -f daily    Create daily habit
bujo habits done "X"            Mark done
bujo habits list                View all

# MOOD
bujo mood quick 2 7 7.5         Quick log
bujo mood today                 View today

# SYNC
bujo sync push                  Upload
bujo sync pull                  Download

# UNDO
bujo undo                       Undo last action
```

---

**Happy Journaling!**

```
   _____
  |     |
  | BuJo|
  |_____|
    | |
   _| |_
  |_____|
```

*CLIBuJo v2.0 - Your terminal, your journal, your way.*
