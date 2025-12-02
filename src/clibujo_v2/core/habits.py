"""Habit tracking operations for CLIBuJo v2."""

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple, Union
from calendar import monthrange

from .db import get_connection, ensure_db, cleanup_undo_history
from .models import Habit, HabitCompletion, HabitStatus, FrequencyType


def validate_habit_name(name: str) -> str:
    """Validate and clean habit name.

    Raises:
        ValueError: If name is empty or whitespace-only
    """
    if not name or not name.strip():
        raise ValueError("Habit name cannot be empty or whitespace-only")
    return name.strip()


def _record_undo(
    conn: sqlite3.Connection,
    action_type: str,
    table_name: str,
    record_id: int,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
) -> None:
    """Record an action for undo capability."""
    conn.execute(
        """
        INSERT INTO undo_history (action_type, table_name, record_id, old_data, new_data)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            action_type,
            table_name,
            record_id,
            json.dumps(old_data) if old_data else None,
            json.dumps(new_data) if new_data else None,
        ),
    )
    cleanup_undo_history(conn)


# Day name mappings
DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_FULL_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_frequency(freq_str: str) -> Tuple[str, int, Optional[str]]:
    """Parse frequency string into (type, target, days).

    Examples:
        'daily' -> ('daily', 1, None)
        'weekly' -> ('weekly', 1, None)
        'weekly:3' -> ('weekly', 3, None)
        'monthly:2' -> ('monthly', 2, None)
        'days:mon,wed,fri' -> ('specific_days', 3, 'mon,wed,fri')

    Raises:
        ValueError: If frequency format is invalid or values are impossible
    """
    freq_str = freq_str.lower().strip()

    if freq_str == "daily":
        return ("daily", 1, None)
    elif freq_str == "weekly":
        return ("weekly", 1, None)
    elif freq_str.startswith("weekly:"):
        target = int(freq_str.split(":")[1])
        if target < 1 or target > 7:
            raise ValueError(f"Weekly target must be 1-7, got {target}")
        return ("weekly", target, None)
    elif freq_str == "monthly":
        return ("monthly", 1, None)
    elif freq_str.startswith("monthly:"):
        target = int(freq_str.split(":")[1])
        if target < 1 or target > 31:
            raise ValueError(f"Monthly target must be 1-31, got {target}")
        return ("monthly", target, None)
    elif freq_str.startswith("days:"):
        days_part = freq_str.split(":")[1]
        if not days_part.strip():
            raise ValueError("Days list cannot be empty")
        # Validate each day is a valid abbreviation
        valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
        days = []
        for d in days_part.split(","):
            day = d.strip()[:3].lower()
            if day not in valid_days:
                raise ValueError(f"Invalid day '{d}'. Use: mon, tue, wed, thu, fri, sat, sun")
            days.append(day)
        if not days:
            raise ValueError("Days list cannot be empty")
        return ("specific_days", len(days), ",".join(days))
    else:
        raise ValueError(f"Invalid frequency format: {freq_str}")


def create_habit(
    name: str,
    frequency: str = "daily",
    category: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Habit:
    """Create a new habit.

    Args:
        name: Habit name (must be unique, case-insensitive)
        frequency: Frequency string (daily, weekly, weekly:N, monthly:N, days:mon,wed,fri)
        category: Optional category for grouping

    Returns:
        The created Habit with id populated

    Raises:
        ValueError: If name is empty/whitespace or frequency is invalid
    """
    # Validate inputs
    name = validate_habit_name(name)
    freq_type, freq_target, freq_days = parse_frequency(frequency)

    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO habits (name, frequency_type, frequency_target, frequency_days, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, freq_type, freq_target, freq_days, category),
        )
        habit_id = cursor.lastrowid

        # Fetch created habit
        cursor = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        habit = Habit.from_row(cursor.fetchone())

        # Record for undo
        _record_undo(conn, "create", "habits", habit_id, new_data=habit.to_dict())

        conn.commit()
        return habit
    finally:
        if should_close:
            conn.close()


def get_habit(habit_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Habit]:
    """Get a habit by ID."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        row = cursor.fetchone()
        return Habit.from_row(row) if row else None
    finally:
        if should_close:
            conn.close()


def get_habit_by_name(name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Habit]:
    """Get a habit by name (case-insensitive)."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            "SELECT * FROM habits WHERE name = ? COLLATE NOCASE",
            (name,),
        )
        row = cursor.fetchone()
        return Habit.from_row(row) if row else None
    finally:
        if should_close:
            conn.close()


def get_all_habits(
    status: Optional[str] = None,
    category: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Habit]:
    """Get all habits with optional filters."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if category:
            conditions.append("category = ?")
            params.append(category)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor = conn.execute(
            f"""
            SELECT * FROM habits
            WHERE {where_clause}
            ORDER BY category, name
            """,
            params,
        )
        return [Habit.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def get_active_habits(conn: Optional[sqlite3.Connection] = None) -> List[Habit]:
    """Get all active habits."""
    return get_all_habits(status="active", conn=conn)


def update_habit(
    habit_id: int,
    name: Optional[str] = None,
    frequency: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Habit]:
    """Update a habit."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get current habit for undo
        cursor = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        row = cursor.fetchone()
        if not row:
            return None

        old_habit = Habit.from_row(row)
        old_data = old_habit.to_dict()

        # Build update query
        updates = ["updated_at = datetime('now')"]
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if frequency is not None:
            freq_type, freq_target, freq_days = parse_frequency(frequency)
            updates.append("frequency_type = ?")
            params.append(freq_type)
            updates.append("frequency_target = ?")
            params.append(freq_target)
            updates.append("frequency_days = ?")
            params.append(freq_days)
        if category is not None:
            updates.append("category = ?")
            params.append(category if category else None)
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        params.append(habit_id)

        conn.execute(
            f"UPDATE habits SET {', '.join(updates)} WHERE id = ?",
            params,
        )

        # Fetch updated habit
        cursor = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        new_habit = Habit.from_row(cursor.fetchone())

        # Record for undo
        _record_undo(conn, "update", "habits", habit_id, old_data=old_data, new_data=new_habit.to_dict())

        conn.commit()
        return new_habit
    finally:
        if should_close:
            conn.close()


def pause_habit(habit_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Habit]:
    """Pause a habit."""
    return update_habit(habit_id, status="paused", conn=conn)


def resume_habit(habit_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Habit]:
    """Resume a paused habit."""
    return update_habit(habit_id, status="active", conn=conn)


def quit_habit(habit_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Habit]:
    """Quit a habit (bad habit you're stopping)."""
    return update_habit(habit_id, status="quit", conn=conn)


def complete_habit_permanently(habit_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Habit]:
    """Mark habit as permanently completed (goal achieved)."""
    return update_habit(habit_id, status="completed", conn=conn)


def delete_habit(habit_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Delete a habit and all its completions."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get habit for undo
        cursor = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        row = cursor.fetchone()
        if not row:
            return False

        old_habit = Habit.from_row(row)

        # Record for undo
        _record_undo(conn, "delete", "habits", habit_id, old_data=old_habit.to_dict())

        # Cascade delete will handle completions
        conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        conn.commit()
        return True
    finally:
        if should_close:
            conn.close()


def record_completion(
    habit_id: int,
    completion_date: Optional[str] = None,
    note: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> HabitCompletion:
    """Record a habit completion.

    Args:
        habit_id: Habit to complete
        completion_date: Date of completion (YYYY-MM-DD), defaults to today
        note: Optional note about the completion

    Returns:
        The created HabitCompletion
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    if completion_date is None:
        completion_date = date.today().isoformat()

    try:
        cursor = conn.execute(
            """
            INSERT INTO habit_completions (habit_id, completion_date, note)
            VALUES (?, ?, ?)
            """,
            (habit_id, completion_date, note),
        )
        completion_id = cursor.lastrowid

        cursor = conn.execute("SELECT * FROM habit_completions WHERE id = ?", (completion_id,))
        completion = HabitCompletion.from_row(cursor.fetchone())

        # Record for undo
        conn.execute(
            """
            INSERT INTO undo_history (action_type, table_name, record_id, new_data)
            VALUES ('create', 'habit_completions', ?, ?)
            """,
            (completion_id, json.dumps({"habit_id": habit_id, "completion_date": completion_date, "note": note})),
        )

        conn.commit()
        return completion
    finally:
        if should_close:
            conn.close()


def remove_completion(
    habit_id: int,
    completion_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Remove a habit completion for a date."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    if completion_date is None:
        completion_date = date.today().isoformat()

    try:
        cursor = conn.execute(
            """
            SELECT * FROM habit_completions
            WHERE habit_id = ? AND completion_date = ?
            """,
            (habit_id, completion_date),
        )
        row = cursor.fetchone()
        if not row:
            return False

        completion = HabitCompletion.from_row(row)

        # Record for undo
        conn.execute(
            """
            INSERT INTO undo_history (action_type, table_name, record_id, old_data)
            VALUES ('delete', 'habit_completions', ?, ?)
            """,
            (
                completion.id,
                json.dumps({"habit_id": habit_id, "completion_date": completion_date, "note": completion.note}),
            ),
        )

        conn.execute(
            "DELETE FROM habit_completions WHERE habit_id = ? AND completion_date = ?",
            (habit_id, completion_date),
        )
        conn.commit()
        return True
    finally:
        if should_close:
            conn.close()


def is_completed_on_date(
    habit_id: int,
    check_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Check if habit was completed on a date."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    if check_date is None:
        check_date = date.today().isoformat()

    try:
        cursor = conn.execute(
            """
            SELECT 1 FROM habit_completions
            WHERE habit_id = ? AND completion_date = ?
            """,
            (habit_id, check_date),
        )
        return cursor.fetchone() is not None
    finally:
        if should_close:
            conn.close()


def get_completions_in_range(
    habit_id: int,
    start_date: str,
    end_date: str,
    conn: Optional[sqlite3.Connection] = None,
) -> List[HabitCompletion]:
    """Get all completions for a habit in a date range."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            """
            SELECT * FROM habit_completions
            WHERE habit_id = ?
              AND completion_date BETWEEN ? AND ?
            ORDER BY completion_date
            """,
            (habit_id, start_date, end_date),
        )
        return [HabitCompletion.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def is_habit_due_on_date(habit: Habit, check_date: date) -> bool:
    """Check if a habit is due on a specific date."""
    if habit.status != "active":
        return False

    if habit.frequency_type == "daily":
        return True
    elif habit.frequency_type == "specific_days":
        day_name = DAY_NAMES[check_date.weekday()]
        return day_name in habit.frequency_days_list
    elif habit.frequency_type in ("weekly", "monthly"):
        # For weekly/monthly with targets, always due (user decides when)
        return True

    return False


def get_habits_due_on_date(
    check_date: Optional[date] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Habit]:
    """Get all habits due on a specific date."""
    if check_date is None:
        check_date = date.today()

    habits = get_active_habits(conn=conn)
    return [h for h in habits if is_habit_due_on_date(h, check_date)]


def get_week_range(target_date: date) -> Tuple[date, date]:
    """Get Monday-Sunday range for a date's week."""
    monday = target_date - timedelta(days=target_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_month_range(target_date: date) -> Tuple[date, date]:
    """Get first and last day of a date's month."""
    first_day = target_date.replace(day=1)
    last_day = target_date.replace(day=monthrange(target_date.year, target_date.month)[1])
    return first_day, last_day


def get_habit_progress(
    habit: Habit,
    target_date: Optional[date] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict:
    """Get progress for a habit.

    Returns dict with:
        - completed: number completed in current period
        - target: target for current period
        - percentage: completion percentage
        - streak: current streak count
        - period: 'day', 'week', or 'month'
    """
    if target_date is None:
        target_date = date.today()

    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        if habit.frequency_type == "daily":
            # Check today only
            completed = 1 if is_completed_on_date(habit.id, target_date.isoformat(), conn) else 0
            target = 1
            period = "day"
            start = target_date
            end = target_date
        elif habit.frequency_type == "specific_days":
            # Check this week for specific days
            start, end = get_week_range(target_date)
            completions = get_completions_in_range(habit.id, start.isoformat(), end.isoformat(), conn)
            completed = len(completions)
            target = habit.frequency_target
            period = "week"
        elif habit.frequency_type == "weekly":
            start, end = get_week_range(target_date)
            completions = get_completions_in_range(habit.id, start.isoformat(), end.isoformat(), conn)
            completed = len(completions)
            target = habit.frequency_target
            period = "week"
        elif habit.frequency_type == "monthly":
            start, end = get_month_range(target_date)
            completions = get_completions_in_range(habit.id, start.isoformat(), end.isoformat(), conn)
            completed = len(completions)
            target = habit.frequency_target
            period = "month"
        else:
            completed = 0
            target = 1
            period = "unknown"
            start = target_date
            end = target_date

        percentage = min(100, int((completed / target) * 100)) if target > 0 else 0

        # Calculate streak
        streak = calculate_streak(habit, target_date, conn)

        return {
            "completed": completed,
            "target": target,
            "percentage": percentage,
            "streak": streak,
            "period": period,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }
    finally:
        if should_close:
            conn.close()


def calculate_streak(
    habit: Habit,
    target_date: Optional[date] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Calculate current streak for a habit."""
    if target_date is None:
        target_date = date.today()

    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        streak = 0
        current_date = target_date

        if habit.frequency_type == "daily":
            # Check consecutive days
            while True:
                if is_completed_on_date(habit.id, current_date.isoformat(), conn):
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break
        elif habit.frequency_type == "weekly" or habit.frequency_type == "specific_days":
            # Check consecutive weeks meeting target
            while True:
                week_start, week_end = get_week_range(current_date)
                completions = get_completions_in_range(
                    habit.id, week_start.isoformat(), week_end.isoformat(), conn
                )
                if len(completions) >= habit.frequency_target:
                    streak += 1
                    current_date = week_start - timedelta(days=1)
                else:
                    break
        elif habit.frequency_type == "monthly":
            # Check consecutive months meeting target
            while True:
                month_start, month_end = get_month_range(current_date)
                completions = get_completions_in_range(
                    habit.id, month_start.isoformat(), month_end.isoformat(), conn
                )
                if len(completions) >= habit.frequency_target:
                    streak += 1
                    current_date = month_start - timedelta(days=1)
                else:
                    break

        return streak
    finally:
        if should_close:
            conn.close()


def get_habit_calendar(
    habit_id: int,
    year: int,
    month: int,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[int, bool]:
    """Get completion calendar for a month.

    Returns dict mapping day number to completion status.
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        start_date = f"{year:04d}-{month:02d}-01"
        days_in_month = monthrange(year, month)[1]
        end_date = f"{year:04d}-{month:02d}-{days_in_month:02d}"

        completions = get_completions_in_range(habit_id, start_date, end_date, conn)
        completed_days = {int(c.completion_date.split("-")[2]) for c in completions}

        return {day: day in completed_days for day in range(1, days_in_month + 1)}
    finally:
        if should_close:
            conn.close()


def get_categories(conn: Optional[sqlite3.Connection] = None) -> List[str]:
    """Get all unique habit categories."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            """
            SELECT DISTINCT category FROM habits
            WHERE category IS NOT NULL
            ORDER BY category
            """
        )
        return [row["category"] for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()
