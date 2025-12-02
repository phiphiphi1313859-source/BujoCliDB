"""Collection CRUD operations for CLIBuJo v2."""

import json
import sqlite3
from datetime import datetime
from typing import Optional, List

from .db import get_connection, ensure_db, cleanup_undo_history
from .models import Collection, CollectionType


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
        VALUES (?, 'collections', ?, ?, ?)
        """,
        (
            action_type,
            record_id,
            json.dumps(old_data) if old_data else None,
            json.dumps(new_data) if new_data else None,
        ),
    )
    cleanup_undo_history(conn)


def create_collection(
    name: str,
    collection_type: str = "project",
    description: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Collection:
    """Create a new collection.

    Args:
        name: Collection name (must be unique, case-insensitive)
        collection_type: 'project', 'tracker', or 'list'
        description: Optional description

    Returns:
        The created Collection with id populated
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO collections (name, type, description)
            VALUES (?, ?, ?)
            """,
            (name, collection_type, description),
        )
        collection_id = cursor.lastrowid

        # Fetch the created collection
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        collection = Collection.from_row(cursor.fetchone())

        # Record for undo
        _record_undo(conn, "create", collection_id, new_data=collection.to_dict())

        conn.commit()
        return collection
    finally:
        if should_close:
            conn.close()


def get_collection(collection_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Collection]:
    """Get a collection by ID."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        row = cursor.fetchone()
        return Collection.from_row(row) if row else None
    finally:
        if should_close:
            conn.close()


def get_collection_by_name(name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Collection]:
    """Get a collection by name (case-insensitive)."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        cursor = conn.execute(
            "SELECT * FROM collections WHERE name = ? COLLATE NOCASE",
            (name,),
        )
        row = cursor.fetchone()
        return Collection.from_row(row) if row else None
    finally:
        if should_close:
            conn.close()


def get_all_collections(
    include_archived: bool = False,
    collection_type: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Collection]:
    """Get all collections.

    Args:
        include_archived: Include archived collections
        collection_type: Filter by type ('project', 'tracker', 'list')

    Returns:
        List of collections
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        conditions = []
        params = []

        if not include_archived:
            conditions.append("archived_at IS NULL")

        if collection_type:
            conditions.append("type = ?")
            params.append(collection_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor = conn.execute(
            f"""
            SELECT * FROM collections
            WHERE {where_clause}
            ORDER BY type, name
            """,
            params,
        )
        return [Collection.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def update_collection(
    collection_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Collection]:
    """Update a collection.

    Only provided fields are updated.
    Returns updated Collection or None if not found.
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get current collection for undo
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        row = cursor.fetchone()
        if not row:
            return None

        old_collection = Collection.from_row(row)
        old_data = old_collection.to_dict()

        # Build update query
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description if description else None)

        if not updates:
            return old_collection

        params.append(collection_id)

        conn.execute(
            f"UPDATE collections SET {', '.join(updates)} WHERE id = ?",
            params,
        )

        # Fetch updated collection
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        new_collection = Collection.from_row(cursor.fetchone())

        # Record for undo
        _record_undo(conn, "update", collection_id, old_data=old_data, new_data=new_collection.to_dict())

        conn.commit()
        return new_collection
    finally:
        if should_close:
            conn.close()


def archive_collection(collection_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Collection]:
    """Archive a collection."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get current collection for undo
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        row = cursor.fetchone()
        if not row:
            return None

        old_collection = Collection.from_row(row)
        old_data = old_collection.to_dict()

        conn.execute(
            "UPDATE collections SET archived_at = datetime('now') WHERE id = ?",
            (collection_id,),
        )

        # Fetch updated collection
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        new_collection = Collection.from_row(cursor.fetchone())

        # Record for undo
        _record_undo(conn, "update", collection_id, old_data=old_data, new_data=new_collection.to_dict())

        conn.commit()
        return new_collection
    finally:
        if should_close:
            conn.close()


def unarchive_collection(collection_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Collection]:
    """Unarchive a collection."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get current collection for undo
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        row = cursor.fetchone()
        if not row:
            return None

        old_collection = Collection.from_row(row)
        old_data = old_collection.to_dict()

        conn.execute(
            "UPDATE collections SET archived_at = NULL WHERE id = ?",
            (collection_id,),
        )

        # Fetch updated collection
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        new_collection = Collection.from_row(cursor.fetchone())

        # Record for undo
        _record_undo(conn, "update", collection_id, old_data=old_data, new_data=new_collection.to_dict())

        conn.commit()
        return new_collection
    finally:
        if should_close:
            conn.close()


def delete_collection(
    collection_id: int,
    delete_entries: bool = False,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Delete a collection.

    Args:
        collection_id: Collection to delete
        delete_entries: If True, delete all entries. If False, unlink them.

    Returns:
        True if deleted
    """
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        # Get collection for undo
        cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        row = cursor.fetchone()
        if not row:
            return False

        old_collection = Collection.from_row(row)

        if delete_entries:
            conn.execute("DELETE FROM entries WHERE collection_id = ?", (collection_id,))
        else:
            conn.execute(
                "UPDATE entries SET collection_id = NULL WHERE collection_id = ?",
                (collection_id,),
            )

        # Record for undo before deleting
        _record_undo(conn, "delete", collection_id, old_data=old_collection.to_dict())

        conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
        conn.commit()
        return True
    finally:
        if should_close:
            conn.close()


def get_collection_stats(
    collection_id: int,
    conn: Optional[sqlite3.Connection] = None,
) -> dict:
    """Get statistics for a collection."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        stats = {"total": 0, "tasks": 0, "events": 0, "notes": 0, "open": 0, "complete": 0}

        cursor = conn.execute(
            """
            SELECT entry_type, status, COUNT(*) as count
            FROM entries
            WHERE collection_id = ?
            GROUP BY entry_type, status
            """,
            (collection_id,),
        )

        for row in cursor.fetchall():
            entry_type = row["entry_type"]
            status = row["status"]
            count = row["count"]

            stats["total"] += count
            stats[entry_type + "s"] = stats.get(entry_type + "s", 0) + count

            if entry_type == "task":
                if status == "complete":
                    stats["complete"] += count
                elif status == "open":
                    stats["open"] += count

        return stats
    finally:
        if should_close:
            conn.close()


def search_collections(
    query: str,
    include_archived: bool = False,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Collection]:
    """Search collections by name."""
    ensure_db()
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        if include_archived:
            cursor = conn.execute(
                """
                SELECT * FROM collections
                WHERE name LIKE ?
                ORDER BY type, name
                """,
                (f"%{query}%",),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM collections
                WHERE name LIKE ?
                  AND archived_at IS NULL
                ORDER BY type, name
                """,
                (f"%{query}%",),
            )
        return [Collection.from_row(row) for row in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()
