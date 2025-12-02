"""Mood tracking models and database operations for CLIBuJo v2."""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from .db import get_connection


@dataclass
class MoodEntry:
    """A daily mood entry."""
    date: str
    mood: Optional[int] = None
    energy: Optional[int] = None
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = None
    irritability: Optional[int] = None
    anxiety: Optional[int] = None
    racing_thoughts: Optional[int] = None
    impulsivity: Optional[int] = None
    concentration: Optional[int] = None
    social_drive: Optional[int] = None
    appetite: Optional[int] = None
    note: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MoodEntry":
        return cls(**dict(row))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WatchData:
    """Daily watch/fitness data."""
    date: str
    steps: Optional[int] = None
    resting_hr: Optional[int] = None
    hrv: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "WatchData":
        return cls(**dict(row))


@dataclass
class Medication:
    """A medication definition."""
    name: str
    dosage: Optional[str] = None
    time_of_day: Optional[str] = None
    active: bool = True
    id: Optional[int] = None
    created_at: Optional[str] = None
    deactivated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Medication":
        data = dict(row)
        data["active"] = bool(data.get("active", 1))
        return cls(**data)


@dataclass
class MedLog:
    """A medication log entry."""
    med_id: int
    date: str
    taken: bool = True
    time_taken: Optional[str] = None
    note: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MedLog":
        data = dict(row)
        data["taken"] = bool(data.get("taken", 1))
        return cls(**data)


@dataclass
class Episode:
    """A mood episode."""
    start_date: str
    type: str
    end_date: Optional[str] = None
    severity: Optional[int] = None
    note: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Episode":
        return cls(**dict(row))


@dataclass
class MoodTrigger:
    """A custom trigger definition."""
    condition: str
    message: str
    active: bool = True
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MoodTrigger":
        data = dict(row)
        data["active"] = bool(data.get("active", 1))
        return cls(**data)


@dataclass
class Baseline:
    """A calculated baseline for a metric."""
    metric: str
    value: float
    std_dev: float
    calculated_at: str
    days_used: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Baseline":
        return cls(**dict(row))


# Mood Entry operations

def get_mood_entry(date_str: str, conn: Optional[sqlite3.Connection] = None) -> Optional[MoodEntry]:
    """Get mood entry for a specific date."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    row = conn.execute(
        "SELECT * FROM mood_entries WHERE date = ?", (date_str,)
    ).fetchone()

    if should_close:
        conn.close()
    return MoodEntry.from_row(row) if row else None


def save_mood_entry(entry: MoodEntry, save_history: bool = True,
                    conn: Optional[sqlite3.Connection] = None) -> MoodEntry:
    """Save or update a mood entry. Returns the saved entry with id."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    now = datetime.now().isoformat()

    existing = conn.execute(
        "SELECT * FROM mood_entries WHERE date = ?", (entry.date,)
    ).fetchone()

    if existing:
        # Save history for undo
        if save_history:
            history_data = json.dumps(dict(existing))
            conn.execute(
                """INSERT OR REPLACE INTO mood_entry_history (entry_id, previous_data, changed_at)
                   VALUES (?, ?, ?)""",
                (existing["id"], history_data, now)
            )

        # Update existing - use COALESCE to merge with existing values
        conn.execute(
            """UPDATE mood_entries SET
               mood = COALESCE(?, mood),
               energy = COALESCE(?, energy),
               sleep_hours = COALESCE(?, sleep_hours),
               sleep_quality = COALESCE(?, sleep_quality),
               irritability = COALESCE(?, irritability),
               anxiety = COALESCE(?, anxiety),
               racing_thoughts = COALESCE(?, racing_thoughts),
               impulsivity = COALESCE(?, impulsivity),
               concentration = COALESCE(?, concentration),
               social_drive = COALESCE(?, social_drive),
               appetite = COALESCE(?, appetite),
               note = COALESCE(?, note),
               updated_at = ?
               WHERE date = ?""",
            (entry.mood, entry.energy, entry.sleep_hours, entry.sleep_quality,
             entry.irritability, entry.anxiety, entry.racing_thoughts,
             entry.impulsivity, entry.concentration, entry.social_drive,
             entry.appetite, entry.note, now, entry.date)
        )
        entry.id = existing["id"]
    else:
        # Insert new
        cursor = conn.execute(
            """INSERT INTO mood_entries
               (date, mood, energy, sleep_hours, sleep_quality, irritability,
                anxiety, racing_thoughts, impulsivity, concentration,
                social_drive, appetite, note, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry.date, entry.mood, entry.energy, entry.sleep_hours,
             entry.sleep_quality, entry.irritability, entry.anxiety,
             entry.racing_thoughts, entry.impulsivity, entry.concentration,
             entry.social_drive, entry.appetite, entry.note, now, now)
        )
        entry.id = cursor.lastrowid

    conn.commit()
    if should_close:
        conn.close()
    return entry


def undo_mood_entry(date_str: str, conn: Optional[sqlite3.Connection] = None) -> Optional[MoodEntry]:
    """Undo the last change to a mood entry. Returns the restored entry or None."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    # Get current entry
    current = conn.execute(
        "SELECT id FROM mood_entries WHERE date = ?", (date_str,)
    ).fetchone()

    if not current:
        if should_close:
            conn.close()
        return None

    # Get history
    history = conn.execute(
        "SELECT previous_data FROM mood_entry_history WHERE entry_id = ?",
        (current["id"],)
    ).fetchone()

    if not history:
        if should_close:
            conn.close()
        return None

    # Restore previous data
    prev = json.loads(history["previous_data"])
    conn.execute(
        """UPDATE mood_entries SET
           mood = ?, energy = ?, sleep_hours = ?, sleep_quality = ?,
           irritability = ?, anxiety = ?, racing_thoughts = ?,
           impulsivity = ?, concentration = ?, social_drive = ?,
           appetite = ?, note = ?, updated_at = ?
           WHERE id = ?""",
        (prev["mood"], prev["energy"], prev["sleep_hours"], prev["sleep_quality"],
         prev["irritability"], prev["anxiety"], prev["racing_thoughts"],
         prev["impulsivity"], prev["concentration"], prev["social_drive"],
         prev["appetite"], prev["note"], datetime.now().isoformat(), current["id"])
    )

    # Delete history (one-level undo)
    conn.execute("DELETE FROM mood_entry_history WHERE entry_id = ?", (current["id"],))

    conn.commit()
    if should_close:
        conn.close()

    return get_mood_entry(date_str)


def get_mood_entries(start_date: str, end_date: str,
                     conn: Optional[sqlite3.Connection] = None) -> List[MoodEntry]:
    """Get mood entries in a date range (inclusive)."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    rows = conn.execute(
        "SELECT * FROM mood_entries WHERE date BETWEEN ? AND ? ORDER BY date",
        (start_date, end_date)
    ).fetchall()

    if should_close:
        conn.close()
    return [MoodEntry.from_row(row) for row in rows]


def get_recent_mood_entries(days: int, conn: Optional[sqlite3.Connection] = None) -> List[MoodEntry]:
    """Get the most recent N days of mood entries."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    rows = conn.execute(
        """SELECT * FROM mood_entries
           ORDER BY date DESC LIMIT ?""",
        (days,)
    ).fetchall()

    if should_close:
        conn.close()
    return [MoodEntry.from_row(row) for row in rows]


# Watch data operations

def get_watch_data(date_str: str, conn: Optional[sqlite3.Connection] = None) -> Optional[WatchData]:
    """Get watch data for a specific date."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    row = conn.execute(
        "SELECT * FROM watch_data WHERE date = ?", (date_str,)
    ).fetchone()

    if should_close:
        conn.close()
    return WatchData.from_row(row) if row else None


def save_watch_data(data: WatchData, conn: Optional[sqlite3.Connection] = None) -> WatchData:
    """Save or update watch data."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    now = datetime.now().isoformat()

    existing = conn.execute(
        "SELECT id FROM watch_data WHERE date = ?", (data.date,)
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE watch_data SET
               steps = COALESCE(?, steps),
               resting_hr = COALESCE(?, resting_hr),
               hrv = COALESCE(?, hrv),
               updated_at = ?
               WHERE date = ?""",
            (data.steps, data.resting_hr, data.hrv, now, data.date)
        )
        data.id = existing["id"]
    else:
        cursor = conn.execute(
            """INSERT INTO watch_data (date, steps, resting_hr, hrv, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data.date, data.steps, data.resting_hr, data.hrv, now, now)
        )
        data.id = cursor.lastrowid

    conn.commit()
    if should_close:
        conn.close()
    return data


# Medication operations

def get_medications(active_only: bool = True,
                    conn: Optional[sqlite3.Connection] = None) -> List[Medication]:
    """Get all medications."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    if active_only:
        rows = conn.execute(
            "SELECT * FROM medications WHERE active = 1 ORDER BY time_of_day, name"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM medications ORDER BY active DESC, time_of_day, name"
        ).fetchall()

    if should_close:
        conn.close()
    return [Medication.from_row(row) for row in rows]


def get_medication_by_name(name: str,
                           conn: Optional[sqlite3.Connection] = None) -> Optional[Medication]:
    """Get a medication by name (case-insensitive)."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    row = conn.execute(
        "SELECT * FROM medications WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()

    if should_close:
        conn.close()
    return Medication.from_row(row) if row else None


def add_medication(med: Medication, conn: Optional[sqlite3.Connection] = None) -> Medication:
    """Add a new medication."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    cursor = conn.execute(
        """INSERT INTO medications (name, dosage, time_of_day, active, created_at)
           VALUES (?, ?, ?, 1, ?)""",
        (med.name, med.dosage, med.time_of_day, datetime.now().isoformat())
    )
    med.id = cursor.lastrowid
    conn.commit()

    if should_close:
        conn.close()
    return med


def deactivate_medication(name: str, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Deactivate a medication (soft delete)."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    cursor = conn.execute(
        """UPDATE medications SET active = 0, deactivated_at = ?
           WHERE name = ? COLLATE NOCASE AND active = 1""",
        (datetime.now().isoformat(), name)
    )
    conn.commit()
    affected = cursor.rowcount

    if should_close:
        conn.close()
    return affected > 0


def log_medication(med_id: int, date_str: str, taken: bool = True,
                   time_taken: Optional[str] = None, note: Optional[str] = None,
                   conn: Optional[sqlite3.Connection] = None) -> MedLog:
    """Log a medication taken/missed."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    conn.execute(
        """INSERT OR REPLACE INTO med_logs (med_id, date, taken, time_taken, note, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (med_id, date_str, 1 if taken else 0, time_taken, note, datetime.now().isoformat())
    )
    conn.commit()

    if should_close:
        conn.close()

    return MedLog(med_id=med_id, date=date_str, taken=taken,
                  time_taken=time_taken, note=note)


def get_med_logs_for_date(date_str: str,
                          conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Get medication logs for a date with medication info."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    rows = conn.execute(
        """SELECT m.name, m.dosage, m.time_of_day, ml.taken, ml.time_taken, ml.note
           FROM medications m
           LEFT JOIN med_logs ml ON m.id = ml.med_id AND ml.date = ?
           WHERE m.active = 1
           ORDER BY m.time_of_day, m.name""",
        (date_str,)
    ).fetchall()

    if should_close:
        conn.close()
    return [dict(row) for row in rows]


# Episode operations

def get_current_episode(conn: Optional[sqlite3.Connection] = None) -> Optional[Episode]:
    """Get the current open episode (no end date)."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    row = conn.execute(
        "SELECT * FROM episodes WHERE end_date IS NULL ORDER BY start_date DESC LIMIT 1"
    ).fetchone()

    if should_close:
        conn.close()
    return Episode.from_row(row) if row else None


def start_episode(ep_type: str, start_date: Optional[str] = None,
                  severity: Optional[int] = None,
                  conn: Optional[sqlite3.Connection] = None) -> Episode:
    """Start a new episode."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    if start_date is None:
        start_date = date.today().isoformat()

    cursor = conn.execute(
        """INSERT INTO episodes (start_date, type, severity, created_at)
           VALUES (?, ?, ?, ?)""",
        (start_date, ep_type, severity, datetime.now().isoformat())
    )
    episode_id = cursor.lastrowid
    conn.commit()

    if should_close:
        conn.close()

    return Episode(id=episode_id, start_date=start_date, type=ep_type, severity=severity)


def end_episode(episode_id: int, end_date: Optional[str] = None,
                note: Optional[str] = None,
                conn: Optional[sqlite3.Connection] = None) -> Episode:
    """End an episode."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    if end_date is None:
        end_date = date.today().isoformat()

    conn.execute(
        "UPDATE episodes SET end_date = ?, note = ? WHERE id = ?",
        (end_date, note, episode_id)
    )
    conn.commit()

    row = conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()

    if should_close:
        conn.close()
    return Episode.from_row(row)


def add_episode(start_date: str, end_date: str, ep_type: str,
                severity: Optional[int] = None, note: Optional[str] = None,
                conn: Optional[sqlite3.Connection] = None) -> Episode:
    """Add a past episode with start and end dates."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    cursor = conn.execute(
        """INSERT INTO episodes (start_date, end_date, type, severity, note, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (start_date, end_date, ep_type, severity, note, datetime.now().isoformat())
    )
    episode_id = cursor.lastrowid
    conn.commit()

    if should_close:
        conn.close()

    return Episode(id=episode_id, start_date=start_date, end_date=end_date,
                   type=ep_type, severity=severity, note=note)


def get_episodes(months: int = 12, conn: Optional[sqlite3.Connection] = None) -> List[Episode]:
    """Get episodes from the last N months."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    rows = conn.execute(
        """SELECT * FROM episodes
           WHERE start_date >= date('now', ?)
           ORDER BY start_date DESC""",
        (f"-{months} months",)
    ).fetchall()

    if should_close:
        conn.close()
    return [Episode.from_row(row) for row in rows]


# Trigger operations

def get_mood_triggers(active_only: bool = True,
                      conn: Optional[sqlite3.Connection] = None) -> List[MoodTrigger]:
    """Get all mood triggers."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    if active_only:
        rows = conn.execute(
            "SELECT * FROM mood_triggers WHERE active = 1"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM mood_triggers").fetchall()

    if should_close:
        conn.close()
    return [MoodTrigger.from_row(row) for row in rows]


def add_mood_trigger(condition: str, message: str,
                     conn: Optional[sqlite3.Connection] = None) -> MoodTrigger:
    """Add a new trigger."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    cursor = conn.execute(
        """INSERT INTO mood_triggers (condition, message, active, created_at)
           VALUES (?, ?, 1, ?)""",
        (condition, message, datetime.now().isoformat())
    )
    trigger_id = cursor.lastrowid
    conn.commit()

    if should_close:
        conn.close()
    return MoodTrigger(id=trigger_id, condition=condition, message=message)


def set_mood_trigger_active(trigger_id: int, active: bool,
                            conn: Optional[sqlite3.Connection] = None) -> bool:
    """Enable or disable a trigger."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    cursor = conn.execute(
        "UPDATE mood_triggers SET active = ? WHERE id = ?",
        (1 if active else 0, trigger_id)
    )
    conn.commit()
    affected = cursor.rowcount

    if should_close:
        conn.close()
    return affected > 0


def delete_mood_trigger(trigger_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Delete a trigger."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    cursor = conn.execute("DELETE FROM mood_triggers WHERE id = ?", (trigger_id,))
    conn.commit()
    affected = cursor.rowcount

    if should_close:
        conn.close()
    return affected > 0


# Baseline operations

def get_baseline(metric: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Baseline]:
    """Get baseline for a metric."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    row = conn.execute(
        "SELECT * FROM baselines WHERE metric = ?", (metric,)
    ).fetchone()

    if should_close:
        conn.close()
    return Baseline.from_row(row) if row else None


def get_all_baselines(conn: Optional[sqlite3.Connection] = None) -> List[Baseline]:
    """Get all baselines."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    rows = conn.execute("SELECT * FROM baselines").fetchall()

    if should_close:
        conn.close()
    return [Baseline.from_row(row) for row in rows]


def save_baseline(baseline: Baseline, conn: Optional[sqlite3.Connection] = None) -> Baseline:
    """Save or update a baseline."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    conn.execute(
        """INSERT OR REPLACE INTO baselines (metric, value, std_dev, calculated_at, days_used)
           VALUES (?, ?, ?, ?, ?)""",
        (baseline.metric, baseline.value, baseline.std_dev,
         baseline.calculated_at, baseline.days_used)
    )
    conn.commit()

    if should_close:
        conn.close()
    return baseline


# Target operations

def get_target(metric: str, conn: Optional[sqlite3.Connection] = None) -> Optional[float]:
    """Get target for a metric."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    row = conn.execute(
        "SELECT value FROM targets WHERE metric = ?", (metric,)
    ).fetchone()

    if should_close:
        conn.close()
    return row["value"] if row else None


def get_all_targets(conn: Optional[sqlite3.Connection] = None) -> Dict[str, float]:
    """Get all targets."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    rows = conn.execute("SELECT metric, value FROM targets").fetchall()

    if should_close:
        conn.close()
    return {row["metric"]: row["value"] for row in rows}


def set_target(metric: str, value: float, conn: Optional[sqlite3.Connection] = None) -> None:
    """Set a target for a metric."""
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    conn.execute(
        """INSERT OR REPLACE INTO targets (metric, value, set_at)
           VALUES (?, ?, ?)""",
        (metric, value, datetime.now().isoformat())
    )
    conn.commit()

    if should_close:
        conn.close()
