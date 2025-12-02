"""Task migration operations for CLIBuJo v2.

Migrations in bullet journaling move open tasks between:
- Daily logs (entry_date)
- Monthly logs (entry_month)
- Collections (collection_id)
"""

import json
import sqlite3
from datetime import date
from typing import Optional, List

from .db import get_connection, ensure_db, cleanup_undo_history
from .models import Entry, Migration
from .entries import get_entry, update_entry


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
        VALUES (?, 'migrations', ?, ?, ?)
        """,
        (
            action_type,
            record_id,
            json.dumps(old_data) if old_data else None,
            json.dumps(new_data) if new_data else None,
        ),
    )
    cleanup_undo_history(conn)


def migrate_to_date(
    entry_id: int,
    target_date: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Entry]:
    """Migrate a task to a specific date.

    Args:
        entry_id: Task to migrate
        target_date: Target date (YYYY-MM-DD)

    Returns:
        Updated Entry or None if not found/not a task
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get current entry
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            return None

        entry = Entry.from_row(row)

        # Only migrate open tasks
        if entry.entry_type != "task" or entry.status != "open":
            return None

        # Record migration history
        cursor = conn.execute(
            """
            INSERT INTO migrations (
                entry_id, from_date, from_month, from_collection_id,
                to_date, to_month, to_collection_id
            ) VALUES (?, ?, ?, ?, ?, NULL, NULL)
            """,
            (entry_id, entry.entry_date, entry.entry_month, entry.collection_id, target_date),
        )
        migration_id = cursor.lastrowid

        # Update entry - mark as migrated at source, create new or update
        # In bujo, migration typically marks old as migrated and references new location
        conn.execute(
            """
            UPDATE entries
            SET status = 'migrated', updated_at = datetime('now')
            WHERE id = ?
            """,
            (entry_id,),
        )

        # Create new entry at target date
        cursor = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), -1) + 1 FROM entries
            WHERE entry_date = ?
            """,
            (target_date,),
        )
        sort_order = cursor.fetchone()[0]

        cursor = conn.execute(
            """
            INSERT INTO entries (
                entry_date, entry_type, status, signifier, content, sort_order
            ) VALUES (?, 'task', 'open', ?, ?, ?)
            """,
            (target_date, entry.signifier, entry.content, sort_order),
        )
        new_entry_id = cursor.lastrowid

        # Update migration record with new entry reference
        conn.execute(
            """
            UPDATE migrations SET to_collection_id = NULL
            WHERE id = ?
            """,
            (migration_id,),
        )

        # Fetch the new entry
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (new_entry_id,))
        new_entry = Entry.from_row(cursor.fetchone())

        conn.commit()
        return new_entry
    finally:
        if should_close:
            conn.close()


def migrate_to_month(
    entry_id: int,
    target_month: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Entry]:
    """Migrate a task to a monthly log (future log style).

    Args:
        entry_id: Task to migrate
        target_month: Target month (YYYY-MM)

    Returns:
        Updated Entry or None if not found/not a task
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get current entry
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            return None

        entry = Entry.from_row(row)

        if entry.entry_type != "task" or entry.status != "open":
            return None

        # Record migration history
        cursor = conn.execute(
            """
            INSERT INTO migrations (
                entry_id, from_date, from_month, from_collection_id,
                to_date, to_month, to_collection_id
            ) VALUES (?, ?, ?, ?, NULL, ?, NULL)
            """,
            (entry_id, entry.entry_date, entry.entry_month, entry.collection_id, target_month),
        )

        # Mark old as scheduled (< symbol in bujo means scheduled for future)
        conn.execute(
            """
            UPDATE entries
            SET status = 'scheduled', updated_at = datetime('now')
            WHERE id = ?
            """,
            (entry_id,),
        )

        # Create new entry in monthly log
        cursor = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), -1) + 1 FROM entries
            WHERE entry_month = ? AND entry_date IS NULL
            """,
            (target_month,),
        )
        sort_order = cursor.fetchone()[0]

        cursor = conn.execute(
            """
            INSERT INTO entries (
                entry_month, entry_type, status, signifier, content, sort_order
            ) VALUES (?, 'task', 'open', ?, ?, ?)
            """,
            (target_month, entry.signifier, entry.content, sort_order),
        )
        new_entry_id = cursor.lastrowid

        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (new_entry_id,))
        new_entry = Entry.from_row(cursor.fetchone())

        conn.commit()
        return new_entry
    finally:
        if should_close:
            conn.close()


def migrate_to_collection(
    entry_id: int,
    collection_id: int,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Entry]:
    """Migrate a task to a collection.

    Args:
        entry_id: Task to migrate
        collection_id: Target collection ID

    Returns:
        Updated Entry or None if not found/not a task
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get current entry
        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            return None

        entry = Entry.from_row(row)

        if entry.entry_type != "task" or entry.status != "open":
            return None

        # Record migration history
        cursor = conn.execute(
            """
            INSERT INTO migrations (
                entry_id, from_date, from_month, from_collection_id,
                to_date, to_month, to_collection_id
            ) VALUES (?, ?, ?, ?, NULL, NULL, ?)
            """,
            (entry_id, entry.entry_date, entry.entry_month, entry.collection_id, collection_id),
        )

        # Mark old as migrated
        conn.execute(
            """
            UPDATE entries
            SET status = 'migrated', updated_at = datetime('now')
            WHERE id = ?
            """,
            (entry_id,),
        )

        # Create new entry in collection
        cursor = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), -1) + 1 FROM entries
            WHERE collection_id = ?
            """,
            (collection_id,),
        )
        sort_order = cursor.fetchone()[0]

        cursor = conn.execute(
            """
            INSERT INTO entries (
                collection_id, entry_type, status, signifier, content, sort_order
            ) VALUES (?, 'task', 'open', ?, ?, ?)
            """,
            (collection_id, entry.signifier, entry.content, sort_order),
        )
        new_entry_id = cursor.lastrowid

        cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (new_entry_id,))
        new_entry = Entry.from_row(cursor.fetchone())

        conn.commit()
        return new_entry
    finally:
        if should_close:
            conn.close()


def migrate_forward(
    entry_id: int,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Entry]:
    """Migrate a task to today.

    This is the most common migration - moving an old open task to today's log.
    """
    today = date.today().isoformat()
    return migrate_to_date(entry_id, today, conn)


def get_migration_history(
    entry_id: int,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Migration]:
    """Get migration history for an entry."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            """
            SELECT * FROM migrations
            WHERE entry_id = ?
            ORDER BY migrated_at DESC
            """,
            (entry_id,),
        )
        return [Migration.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def get_tasks_needing_migration(
    before_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Entry]:
    """Get open tasks that may need migration.

    Returns tasks that are:
    - Open
    - Either have a date before the specified date
    - Or are in a monthly log for a past month
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    if before_date is None:
        before_date = date.today().isoformat()

    # Get current month for monthly log comparison
    current_month = before_date[:7]

    try:
        cursor = conn.execute(
            """
            SELECT * FROM entries
            WHERE entry_type = 'task'
              AND status = 'open'
              AND (
                  (entry_date IS NOT NULL AND entry_date < ?)
                  OR (entry_month IS NOT NULL AND entry_month < ? AND entry_date IS NULL)
              )
            ORDER BY entry_date, entry_month, sort_order
            """,
            (before_date, current_month),
        )
        return [Entry.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def bulk_migrate_to_today(
    entry_ids: List[int],
    conn: Optional[sqlite3.Connection] = None,
) -> List[Entry]:
    """Migrate multiple tasks to today.

    Returns list of newly created entries.
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        new_entries = []
        today = date.today().isoformat()

        for entry_id in entry_ids:
            new_entry = migrate_to_date(entry_id, today, conn)
            if new_entry:
                new_entries.append(new_entry)

        return new_entries
    finally:
        if should_close:
            conn.close()


def get_migration_stats(
    conn: Optional[sqlite3.Connection] = None,
) -> dict:
    """Get migration statistics."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Total migrations
        cursor = conn.execute("SELECT COUNT(*) FROM migrations")
        total = cursor.fetchone()[0]

        # Migrations by destination type
        cursor = conn.execute(
            """
            SELECT
                CASE
                    WHEN to_date IS NOT NULL THEN 'to_date'
                    WHEN to_month IS NOT NULL THEN 'to_month'
                    WHEN to_collection_id IS NOT NULL THEN 'to_collection'
                    ELSE 'unknown'
                END as dest_type,
                COUNT(*) as count
            FROM migrations
            GROUP BY dest_type
            """
        )
        by_type = {row["dest_type"]: row["count"] for row in cursor.fetchall()}

        return {
            "total": total,
            "to_date": by_type.get("to_date", 0),
            "to_month": by_type.get("to_month", 0),
            "to_collection": by_type.get("to_collection", 0),
        }
    finally:
        if should_close:
            conn.close()
