"""Undo system for CLIBuJo v2.

Provides 50 levels of undo for entries, collections, and habits.
"""

import json
import sqlite3
from typing import Optional, List, Dict, Any

from .db import get_connection, ensure_db
from .models import UndoAction


def get_undo_history(
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> List[UndoAction]:
    """Get undo history, most recent first."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            """
            SELECT * FROM undo_history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [UndoAction.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def get_last_action(conn: Optional[sqlite3.Connection] = None) -> Optional[UndoAction]:
    """Get the most recent undoable action."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            """
            SELECT * FROM undo_history
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        return UndoAction.from_row(row) if row else None
    finally:
        if should_close:
            conn.close()


def undo_last_action(conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Undo the most recent action.

    Returns dict with:
        - action: The action that was undone
        - success: Whether undo succeeded
        - message: Description of what was undone
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get last action
        cursor = conn.execute(
            """
            SELECT * FROM undo_history
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return {"action": None, "success": False, "message": "Nothing to undo"}

        action = UndoAction.from_row(row)
        old_data = json.loads(action.old_data) if action.old_data else None
        new_data = json.loads(action.new_data) if action.new_data else None

        message = ""
        success = True

        if action.action_type == "create":
            # Undo create = delete the record
            conn.execute(
                f"DELETE FROM {action.table_name} WHERE id = ?",
                (action.record_id,),
            )
            message = f"Deleted {action.table_name} #{action.record_id}"

        elif action.action_type == "delete":
            # Undo delete = recreate the record
            if old_data:
                # Remove auto-generated fields that would conflict
                old_data.pop("id", None)
                old_data.pop("created_at", None)
                old_data.pop("updated_at", None)

                columns = ", ".join(old_data.keys())
                placeholders = ", ".join("?" * len(old_data))

                cursor = conn.execute(
                    f"INSERT INTO {action.table_name} ({columns}) VALUES ({placeholders})",
                    list(old_data.values()),
                )
                new_id = cursor.lastrowid
                message = f"Restored {action.table_name} (new id: #{new_id})"
            else:
                success = False
                message = "Cannot undo delete: no data saved"

        elif action.action_type == "update":
            # Undo update = restore old values
            if old_data:
                # Build update from old_data, excluding id and timestamps
                update_data = {
                    k: v
                    for k, v in old_data.items()
                    if k not in ("id", "created_at", "updated_at")
                }

                set_clause = ", ".join(f"{k} = ?" for k in update_data.keys())
                values = list(update_data.values()) + [action.record_id]

                conn.execute(
                    f"UPDATE {action.table_name} SET {set_clause} WHERE id = ?",
                    values,
                )
                message = f"Restored {action.table_name} #{action.record_id} to previous state"
            else:
                success = False
                message = "Cannot undo update: no previous data saved"

        else:
            success = False
            message = f"Unknown action type: {action.action_type}"

        # Remove the undone action from history
        conn.execute("DELETE FROM undo_history WHERE id = ?", (action.id,))
        conn.commit()

        return {
            "action": {
                "type": action.action_type,
                "table": action.table_name,
                "record_id": action.record_id,
            },
            "success": success,
            "message": message,
        }
    finally:
        if should_close:
            conn.close()


def undo_multiple(
    count: int = 1,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Undo multiple actions.

    Args:
        count: Number of actions to undo (max 50)

    Returns:
        List of undo results
    """
    count = min(count, 50)
    results = []

    for _ in range(count):
        result = undo_last_action(conn)
        if not result or not result.get("success"):
            break
        results.append(result)

    return results


def clear_undo_history(conn: Optional[sqlite3.Connection] = None) -> int:
    """Clear all undo history.

    Returns number of entries cleared.
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute("SELECT COUNT(*) FROM undo_history")
        count = cursor.fetchone()[0]

        conn.execute("DELETE FROM undo_history")
        conn.commit()

        return count
    finally:
        if should_close:
            conn.close()


def describe_action(action: UndoAction) -> str:
    """Get human-readable description of an action."""
    old_data = json.loads(action.old_data) if action.old_data else {}
    new_data = json.loads(action.new_data) if action.new_data else {}

    table_friendly = {
        "entries": "entry",
        "collections": "collection",
        "habits": "habit",
        "habit_completions": "habit completion",
        "migrations": "migration",
    }.get(action.table_name, action.table_name)

    if action.action_type == "create":
        # Show what was created
        name = new_data.get("content") or new_data.get("name") or f"#{action.record_id}"
        if len(name) > 40:
            name = name[:37] + "..."
        return f"Created {table_friendly}: {name}"

    elif action.action_type == "delete":
        name = old_data.get("content") or old_data.get("name") or f"#{action.record_id}"
        if len(name) > 40:
            name = name[:37] + "..."
        return f"Deleted {table_friendly}: {name}"

    elif action.action_type == "update":
        name = old_data.get("content") or old_data.get("name") or f"#{action.record_id}"
        if len(name) > 30:
            name = name[:27] + "..."

        # Try to describe what changed
        changes = []
        for key in new_data:
            if key in ("id", "created_at", "updated_at"):
                continue
            if old_data.get(key) != new_data.get(key):
                old_val = old_data.get(key)
                new_val = new_data.get(key)
                if key == "status":
                    changes.append(f"{old_val} -> {new_val}")
                else:
                    changes.append(key)

        change_desc = ", ".join(changes[:3])
        if len(changes) > 3:
            change_desc += f" (+{len(changes) - 3} more)"

        return f"Updated {table_friendly} {name}: {change_desc}"

    return f"{action.action_type} {table_friendly} #{action.record_id}"


def get_undo_preview(
    count: int = 5,
    conn: Optional[sqlite3.Connection] = None,
) -> List[str]:
    """Get preview of recent undo actions.

    Returns list of human-readable descriptions.
    """
    actions = get_undo_history(limit=count, conn=conn)
    return [describe_action(action) for action in actions]
