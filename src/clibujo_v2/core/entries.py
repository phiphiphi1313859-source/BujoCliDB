"""Entry CRUD operations with FTS and undo support for CLIBuJo v2."""

import json
import re
import sqlite3
from datetime import date, datetime
from typing import Optional, List, Tuple

from .db import get_connection, ensure_db, cleanup_undo_history
from .models import Entry, EntryType, TaskStatus, Signifier


def validate_content(content: str) -> str:
    """Validate and clean content string.

    Raises:
        ValueError: If content is empty or whitespace-only
    """
    if not content or not content.strip():
        raise ValueError("Content cannot be empty or whitespace-only")
    return content.strip()


def validate_date(date_str: str) -> str:
    """Validate date string is in YYYY-MM-DD format.

    Raises:
        ValueError: If date format is invalid
    """
    if not date_str:
        raise ValueError("Date cannot be empty")

    # Check format with regex
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError(f"Invalid date format '{date_str}'. Use YYYY-MM-DD")

    # Validate it's a real date
    try:
        year, month, day = map(int, date_str.split('-'))
        datetime(year, month, day)  # Will raise if invalid
    except ValueError:
        raise ValueError(f"Invalid date '{date_str}'. Check month and day values")

    return date_str


def validate_month(month_str: str) -> str:
    """Validate month string is in YYYY-MM format.

    Raises:
        ValueError: If month format is invalid
    """
    if not month_str:
        raise ValueError("Month cannot be empty")

    # Check format with regex
    if not re.match(r'^\d{4}-\d{2}$', month_str):
        raise ValueError(f"Invalid month format '{month_str}'. Use YYYY-MM")

    # Validate month is 01-12
    year, month = map(int, month_str.split('-'))
    if month < 1 or month > 12:
        raise ValueError(f"Invalid month '{month_str}'. Month must be 01-12")

    return month_str


def escape_fts_query(query: str) -> str:
    """Escape special characters for FTS5 queries.

    FTS5 uses certain characters as operators. This escapes them
    so they're treated as literal characters.
    """
    # Characters that need escaping in FTS5
    # Wrap the query in double quotes to treat it as a phrase/literal
    # Also escape any internal double quotes
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def _record_undo(
    conn: sqlite3.Connection,
    action_type: str,
    record_id: int,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
) -> None:
    """Record an action for undo capability."""
    conn.execute(
        """
        INSERT INTO undo_history (action_type, table_name, record_id, old_data, new_data)
        VALUES (?, 'entries', ?, ?, ?)
        """,
        (
            action_type,
            record_id,
            json.dumps(old_data) if old_data else None,
            json.dumps(new_data) if new_data else None,
        ),
    )
    cleanup_undo_history(conn)


def create_entry(
    content: str,
    entry_type: str = "task",
    entry_date: Optional[str] = None,
    entry_month: Optional[str] = None,
    collection_id: Optional[int] = None,
    status: Optional[str] = None,
    signifier: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Entry:
    """Create a new entry.

    Args:
        content: The entry content text
        entry_type: 'task', 'event', or 'note'
        entry_date: YYYY-MM-DD for daily entries
        entry_month: YYYY-MM for monthly/future entries
        collection_id: Optional collection to attach to
        status: Task status (only for tasks)
        signifier: Optional signifier (priority, inspiration, etc.)
        conn: Optional existing connection

    Returns:
        The created Entry with id populated

    Raises:
        ValueError: If content is empty/whitespace or date format is invalid
    """
    # Validate inputs
    content = validate_content(content)
    if entry_date:
        entry_date = validate_date(entry_date)
    if entry_month:
        entry_month = validate_month(entry_month)

    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Default status for tasks
        if entry_type == "task" and status is None:
            status = "open"
        elif entry_type != "task":
            status = None

        # Get next sort order for the context
        cursor = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), -1) + 1
            FROM entries
            WHERE (entry_date = ? OR (entry_date IS NULL AND ? IS NULL))
              AND (entry_month = ? OR (entry_month IS NULL AND ? IS NULL))
              AND (collection_id = ? OR (collection_id IS NULL AND ? IS NULL))
            """,
            (entry_date, entry_date, entry_month, entry_month, collection_id, collection_id),
        )
        sort_order = cursor.fetchone()[0]

        cursor = conn.execute(
            """
            INSERT INTO entries (
                collection_id, entry_date, entry_month, entry_type,
                status, signifier, content, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (collection_id, entry_date, entry_month, entry_type, status, signifier, content, sort_order),
        )
        entry_id = cursor.lastrowid

        # Fetch the created entry
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        entry = Entry.from_row(cursor.fetchone())

        # Record for undo
        _record_undo(conn, "create", entry_id, new_data=entry.to_dict())

        conn.commit()
        return entry
    finally:
        if should_close:
            conn.close()


def get_entry(entry_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Entry]:
    """Get an entry by ID."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        return Entry.from_row(row) if row else None
    finally:
        if should_close:
            conn.close()


def get_entries_by_date(
    entry_date: str,
    include_tasks: bool = True,
    include_events: bool = True,
    include_notes: bool = True,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Entry]:
    """Get entries for a specific date."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        types = []
        if include_tasks:
            types.append("task")
        if include_events:
            types.append("event")
        if include_notes:
            types.append("note")

        if not types:
            return []

        placeholders = ",".join("?" * len(types))
        cursor = conn.execute(
            f"""
            SELECT * FROM entries
            WHERE entry_date = ?
              AND entry_type IN ({placeholders})
            ORDER BY sort_order, created_at
            """,
            (entry_date, *types),
        )
        return [Entry.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def get_entries_by_month(
    entry_month: str,
    include_tasks: bool = True,
    include_events: bool = True,
    include_notes: bool = True,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Entry]:
    """Get entries for a specific month (future log style)."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        types = []
        if include_tasks:
            types.append("task")
        if include_events:
            types.append("event")
        if include_notes:
            types.append("note")

        if not types:
            return []

        placeholders = ",".join("?" * len(types))
        cursor = conn.execute(
            f"""
            SELECT * FROM entries
            WHERE entry_month = ?
              AND entry_date IS NULL
              AND entry_type IN ({placeholders})
            ORDER BY sort_order, created_at
            """,
            (entry_month, *types),
        )
        return [Entry.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def get_entries_by_collection(
    collection_id: int,
    include_completed: bool = True,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Entry]:
    """Get entries for a specific collection."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        if include_completed:
            cursor = conn.execute(
                """
                SELECT * FROM entries
                WHERE collection_id = ?
                ORDER BY sort_order, created_at
                """,
                (collection_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM entries
                WHERE collection_id = ?
                  AND (entry_type != 'task' OR status NOT IN ('complete', 'cancelled'))
                ORDER BY sort_order, created_at
                """,
                (collection_id,),
            )
        return [Entry.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def get_open_tasks(
    before_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Entry]:
    """Get all open tasks, optionally before a certain date."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        if before_date:
            cursor = conn.execute(
                """
                SELECT * FROM entries
                WHERE entry_type = 'task'
                  AND status = 'open'
                  AND entry_date < ?
                ORDER BY entry_date, sort_order
                """,
                (before_date,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM entries
                WHERE entry_type = 'task'
                  AND status = 'open'
                ORDER BY entry_date, entry_month, sort_order
                """
            )
        return [Entry.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def update_entry(
    entry_id: int,
    content: Optional[str] = None,
    status: Optional[str] = None,
    signifier: Optional[str] = None,
    entry_date: Optional[str] = None,
    entry_month: Optional[str] = None,
    collection_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Entry]:
    """Update an entry.

    Only provided fields are updated. Pass empty string to clear signifier.
    Returns updated Entry or None if not found.
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get current entry for undo
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            return None

        old_entry = Entry.from_row(row)
        old_data = old_entry.to_dict()

        # Build update query dynamically
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
            # Set completed_at if completing
            if status == "complete":
                updates.append("completed_at = datetime('now')")
            elif old_entry.status == "complete":
                updates.append("completed_at = NULL")
        if signifier is not None:
            updates.append("signifier = ?")
            params.append(signifier if signifier else None)
        if entry_date is not None:
            updates.append("entry_date = ?")
            params.append(entry_date if entry_date else None)
        if entry_month is not None:
            updates.append("entry_month = ?")
            params.append(entry_month if entry_month else None)
        if collection_id is not None:
            updates.append("collection_id = ?")
            params.append(collection_id if collection_id != -1 else None)

        if not updates:
            return old_entry

        updates.append("updated_at = datetime('now')")
        params.append(entry_id)

        conn.execute(
            f"UPDATE entries SET {', '.join(updates)} WHERE id = ?",
            params,
        )

        # Fetch updated entry
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        new_entry = Entry.from_row(cursor.fetchone())

        # Record for undo
        _record_undo(conn, "update", entry_id, old_data=old_data, new_data=new_entry.to_dict())

        conn.commit()
        return new_entry
    finally:
        if should_close:
            conn.close()


def complete_entry(entry_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Entry]:
    """Mark a task as complete."""
    return update_entry(entry_id, status="complete", conn=conn)


def cancel_entry(entry_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Entry]:
    """Mark a task as cancelled."""
    return update_entry(entry_id, status="cancelled", conn=conn)


def reopen_entry(entry_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Entry]:
    """Reopen a completed/cancelled task."""
    return update_entry(entry_id, status="open", conn=conn)


def delete_entry(entry_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Delete an entry. Returns True if deleted."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get entry for undo
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            return False

        old_entry = Entry.from_row(row)

        # Record for undo before deleting
        _record_undo(conn, "delete", entry_id, old_data=old_entry.to_dict())

        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()
        return True
    finally:
        if should_close:
            conn.close()


def search_entries(
    query: str,
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Entry]:
    """Full-text search entries.

    Special characters are escaped to prevent FTS5 syntax errors.
    """
    if not query or not query.strip():
        return []

    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Escape special characters for FTS5
        escaped_query = escape_fts_query(query.strip())

        cursor = conn.execute(
            """
            SELECT e.* FROM entries e
            JOIN entries_fts fts ON e.id = fts.rowid
            WHERE entries_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (escaped_query, limit),
        )
        return [Entry.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def get_entries_date_range(
    start_date: str,
    end_date: str,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Entry]:
    """Get all entries within a date range."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            """
            SELECT * FROM entries
            WHERE entry_date BETWEEN ? AND ?
            ORDER BY entry_date, sort_order
            """,
            (start_date, end_date),
        )
        return [Entry.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def reorder_entry(
    entry_id: int,
    new_position: int,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Reorder an entry within its context (date/month/collection)."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get entry
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            return False

        entry = Entry.from_row(row)
        old_position = entry.sort_order

        if old_position == new_position:
            return True

        # Get all entries in same context
        if entry.collection_id:
            context_clause = "collection_id = ?"
            context_param = entry.collection_id
        elif entry.entry_date:
            context_clause = "entry_date = ?"
            context_param = entry.entry_date
        elif entry.entry_month:
            context_clause = "entry_month = ? AND entry_date IS NULL"
            context_param = entry.entry_month
        else:
            return False

        # Shift other entries
        if new_position < old_position:
            conn.execute(
                f"""
                UPDATE entries
                SET sort_order = sort_order + 1
                WHERE {context_clause}
                  AND sort_order >= ?
                  AND sort_order < ?
                  AND id != ?
                """,
                (context_param, new_position, old_position, entry_id),
            )
        else:
            conn.execute(
                f"""
                UPDATE entries
                SET sort_order = sort_order - 1
                WHERE {context_clause}
                  AND sort_order > ?
                  AND sort_order <= ?
                  AND id != ?
                """,
                (context_param, old_position, new_position, entry_id),
            )

        # Update entry position
        conn.execute(
            "UPDATE entries SET sort_order = ? WHERE id = ?",
            (new_position, entry_id),
        )

        conn.commit()
        return True
    finally:
        if should_close:
            conn.close()


def get_entry_count_by_status(
    conn: Optional[sqlite3.Connection] = None,
) -> dict:
    """Get count of entries by status."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM entries
            WHERE entry_type = 'task'
            GROUP BY status
            """
        )
        return {row["status"]: row["count"] for row in cursor.fetchall()}
    finally:
        if should_close:
            conn.close()
