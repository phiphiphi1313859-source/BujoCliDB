# CLIBuJo TL;DR

Quick reference for CLIBuJo v2. For full docs, see [MANUAL.md](MANUAL.md).

---

## Install

```bash
git clone https://github.com/phiphiphi1313859-source/BujoCliDB.git
cd BujoCliDB
pip install -e .
bujo init
```

---

## Daily Use

```bash
bujo                      # View today
bujo add "Task"           # Add task
bujo add "Meeting" -t event   # Add event
bujo add "*Priority task" # Priority task
bujo done 1               # Complete task #1
bujo view yesterday       # View other days
```

---

## Habits

```bash
bujo habits add "Exercise" -f daily
bujo habits add "Gym" -f weekly:3
bujo habits done "Exercise"
bujo habits today
bujo habits calendar "Exercise"
```

---

## Mood Tracking

```bash
bujo mood quick 2 7 7.5   # Mood(+2) Energy(7) Sleep(7.5h)
bujo mood today           # View today's mood
bujo mood week            # Week overview
bujo mood meds add "Med" --dose "10mg"
bujo mood episode start -t depression
```

---

## Collections

```bash
bujo collections create "Project X" -t project
bujo add "Task" -c "Project X"
bujo collections view "Project X"
```

---

## Migration

```bash
bujo migrate review       # See old open tasks
bujo migrate forward 5    # Move task #5 to today
bujo migrate bulk         # Move all old tasks
```

---

## Export PDF

```bash
bujo export today
bujo export week
bujo export month 2025-12
bujo export mood 2025-11-01 2025-11-30   # For therapy
bujo export mood-month                    # Current month
```

---

## Sync

```bash
bujo sync push            # Upload to cloud
bujo sync pull            # Download from cloud
```

---

## Undo

```bash
bujo undo                 # Undo last action
```

---

## Symbols

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Open task |
| `[x]` | Done |
| `[>]` | Migrated |
| `o` | Event |
| `-` | Note |
| `*` | Priority |
| `!` | Inspiration |
| `?` | Explore |

---

## Help

```bash
bujo --help
bujo habits --help
bujo mood --help
```
