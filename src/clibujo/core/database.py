"""SQLite database management for CLIBuJo"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Generator, Optional

from .models import EntryRecord, UndoAction


class Database:
    """SQLite database wrapper for CLIBuJo cache"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection"""
        if self._connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys and WAL mode for better performance
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database cursor"""
        cur = self.connection.cursor()
        try:
            yield cur
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    def close(self) -> None:
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def init_schema(self) -> None:
        """Initialize database schema"""
        with self.cursor() as cur:
            # Core entries table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_ref TEXT UNIQUE NOT NULL,

                    -- Source file reference
                    source_file TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    raw_line TEXT NOT NULL,

                    -- Entry content
                    entry_type TEXT NOT NULL,
                    status TEXT,
                    signifier TEXT,
                    content TEXT NOT NULL,

                    -- Temporal context
                    entry_date DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,

                    -- Organizational context
                    collection TEXT,
                    month TEXT,

                    -- Migration tracking
                    migrated_to TEXT,
                    migrated_from TEXT
                )
            """)

            # Full-text search virtual table
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                    content,
                    content='entries',
                    content_rowid='id'
                )
            """)

            # Triggers to keep FTS in sync
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
                    INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
                END
            """)

            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
                    INSERT INTO entries_fts(entries_fts, rowid, content)
                    VALUES('delete', old.id, old.content);
                END
            """)

            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
                    INSERT INTO entries_fts(entries_fts, rowid, content)
                    VALUES('delete', old.id, old.content);
                    INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
                END
            """)

            # File tracking for incremental reindex
            cur.execute("""
                CREATE TABLE IF NOT EXISTS file_hashes (
                    file_path TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Undo history
            cur.execute("""
                CREATE TABLE IF NOT EXISTS undo_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    old_content TEXT,
                    new_content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entries_ref ON entries(entry_ref)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(entry_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(entry_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entries_collection ON entries(collection)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entries_month ON entries(month)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entries_source ON entries(source_file)")

    def clear_entries(self) -> None:
        """Clear all entries (for full reindex)"""
        with self.cursor() as cur:
            cur.execute("DELETE FROM entries")
            cur.execute("DELETE FROM file_hashes")

    def clear_file_entries(self, source_file: str) -> None:
        """Clear entries for a specific file"""
        with self.cursor() as cur:
            cur.execute("DELETE FROM entries WHERE source_file = ?", (source_file,))

    def insert_entry(
        self,
        entry_ref: str,
        source_file: str,
        line_number: int,
        raw_line: str,
        entry_type: str,
        content: str,
        status: Optional[str] = None,
        signifier: Optional[str] = None,
        entry_date: Optional[date] = None,
        collection: Optional[str] = None,
        month: Optional[str] = None,
        migrated_to: Optional[str] = None,
        migrated_from: Optional[str] = None,
    ) -> int:
        """Insert a new entry"""
        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO entries
                (entry_ref, source_file, line_number, raw_line, entry_type,
                 status, signifier, content, entry_date, collection, month,
                 migrated_to, migrated_from)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_ref, source_file, line_number, raw_line, entry_type,
                status, signifier, content, entry_date, collection, month,
                migrated_to, migrated_from
            ))
            return cur.lastrowid

    def get_entry_by_ref(self, entry_ref: str) -> Optional[EntryRecord]:
        """Get entry by reference"""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM entries WHERE entry_ref = ?", (entry_ref,))
            row = cur.fetchone()
            if row:
                return self._row_to_entry(row)
            return None

    def get_entry_by_ref_prefix(self, prefix: str) -> Optional[EntryRecord]:
        """Get entry by reference prefix (for short refs)"""
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM entries WHERE entry_ref LIKE ? LIMIT 2",
                (prefix + "%",)
            )
            rows = cur.fetchall()
            if len(rows) == 1:
                return self._row_to_entry(rows[0])
            return None

    def get_entries_by_date(self, entry_date: date) -> list[EntryRecord]:
        """Get all entries for a specific date"""
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM entries WHERE entry_date = ? ORDER BY line_number",
                (entry_date,)
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def get_entries_by_file(self, source_file: str) -> list[EntryRecord]:
        """Get all entries from a specific file"""
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM entries WHERE source_file = ? ORDER BY line_number",
                (source_file,)
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def get_entries_by_month(self, month: str) -> list[EntryRecord]:
        """Get all entries for a month (YYYY-MM format)"""
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM entries WHERE month = ? ORDER BY entry_date, line_number",
                (month,)
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def get_entries_by_collection(self, collection: str) -> list[EntryRecord]:
        """Get all entries in a collection"""
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM entries WHERE collection = ? ORDER BY line_number",
                (collection,)
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def get_open_tasks(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        collection: Optional[str] = None,
    ) -> list[EntryRecord]:
        """Get all open tasks with optional filters"""
        query = "SELECT * FROM entries WHERE entry_type = 'task' AND status = 'open'"
        params: list = []

        if from_date:
            query += " AND entry_date >= ?"
            params.append(from_date)
        if to_date:
            query += " AND entry_date <= ?"
            params.append(to_date)
        if collection:
            query += " AND collection = ?"
            params.append(collection)

        query += " ORDER BY entry_date DESC, line_number"

        with self.cursor() as cur:
            cur.execute(query, params)
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def get_tasks(
        self,
        status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        collection: Optional[str] = None,
        signifier: Optional[str] = None,
    ) -> list[EntryRecord]:
        """Get tasks with filters"""
        query = "SELECT * FROM entries WHERE entry_type = 'task'"
        params: list = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if from_date:
            query += " AND entry_date >= ?"
            params.append(from_date)
        if to_date:
            query += " AND entry_date <= ?"
            params.append(to_date)
        if collection:
            query += " AND collection = ?"
            params.append(collection)
        if signifier:
            query += " AND signifier = ?"
            params.append(signifier)

        query += " ORDER BY entry_date DESC, line_number"

        with self.cursor() as cur:
            cur.execute(query, params)
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def search(self, query: str, limit: int = 50) -> list[tuple[EntryRecord, str]]:
        """Full-text search, returns entries with snippets"""
        with self.cursor() as cur:
            cur.execute("""
                SELECT e.*, snippet(entries_fts, 0, '>>>', '<<<', '...', 32) as snippet
                FROM entries e
                JOIN entries_fts ON e.id = entries_fts.rowid
                WHERE entries_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))

            results = []
            for row in cur.fetchall():
                entry = self._row_to_entry(row)
                snippet = row["snippet"]
                results.append((entry, snippet))
            return results

    def get_stats(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> dict:
        """Get task statistics"""
        query_base = "SELECT * FROM entries WHERE entry_type = 'task'"
        params: list = []

        if year:
            query_base += " AND strftime('%Y', entry_date) = ?"
            params.append(str(year))
        if month:
            query_base += " AND strftime('%m', entry_date) = ?"
            params.append(f"{month:02d}")

        with self.cursor() as cur:
            # Overall stats
            cur.execute(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'migrated' THEN 1 ELSE 0 END) as migrated,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open
                FROM entries WHERE entry_type = 'task'
                {"AND strftime('%Y', entry_date) = ?" if year else ""}
                {"AND strftime('%m', entry_date) = ?" if month else ""}
            """, params)
            overall = dict(cur.fetchone())

            # Monthly breakdown
            cur.execute(f"""
                SELECT
                    strftime('%Y-%m', entry_date) as month,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed
                FROM entries
                WHERE entry_type = 'task' AND entry_date IS NOT NULL
                {"AND strftime('%Y', entry_date) = ?" if year else ""}
                GROUP BY month
                ORDER BY month DESC
            """, [str(year)] if year else [])
            monthly = [dict(row) for row in cur.fetchall()]

            # Collection stats
            cur.execute(f"""
                SELECT
                    collection,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed
                FROM entries
                WHERE entry_type = 'task' AND collection IS NOT NULL
                {"AND strftime('%Y', entry_date) = ?" if year else ""}
                GROUP BY collection
                ORDER BY total DESC
                LIMIT 10
            """, [str(year)] if year else [])
            collections = [dict(row) for row in cur.fetchall()]

        return {
            "overall": overall,
            "monthly": monthly,
            "collections": collections,
        }

    def get_file_hash(self, file_path: str) -> Optional[str]:
        """Get stored hash for a file"""
        with self.cursor() as cur:
            cur.execute(
                "SELECT content_hash FROM file_hashes WHERE file_path = ?",
                (file_path,)
            )
            row = cur.fetchone()
            return row["content_hash"] if row else None

    def set_file_hash(self, file_path: str, content_hash: str) -> None:
        """Set hash for a file"""
        with self.cursor() as cur:
            cur.execute("""
                INSERT OR REPLACE INTO file_hashes (file_path, content_hash, indexed_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (file_path, content_hash))

    def get_all_indexed_files(self) -> list[str]:
        """Get list of all indexed file paths"""
        with self.cursor() as cur:
            cur.execute("SELECT file_path FROM file_hashes")
            return [row["file_path"] for row in cur.fetchall()]

    def delete_file_hash(self, file_path: str) -> None:
        """Delete hash record for a file"""
        with self.cursor() as cur:
            cur.execute("DELETE FROM file_hashes WHERE file_path = ?", (file_path,))

    def update_entry_status(
        self,
        entry_ref: str,
        status: str,
        completed_at: Optional[datetime] = None,
    ) -> None:
        """Update entry status"""
        with self.cursor() as cur:
            if completed_at:
                cur.execute(
                    "UPDATE entries SET status = ?, completed_at = ? WHERE entry_ref = ?",
                    (status, completed_at, entry_ref)
                )
            else:
                cur.execute(
                    "UPDATE entries SET status = ? WHERE entry_ref = ?",
                    (status, entry_ref)
                )

    def add_undo_action(self, action: UndoAction) -> None:
        """Add an action to undo history"""
        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO undo_history
                (action_type, file_path, line_number, old_content, new_content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                action.action_type,
                action.file_path,
                action.line_number,
                action.old_content,
                action.new_content,
                action.timestamp,
            ))

    def get_last_undo_action(self) -> Optional[UndoAction]:
        """Get the most recent undo action"""
        with self.cursor() as cur:
            cur.execute("""
                SELECT * FROM undo_history ORDER BY id DESC LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                return UndoAction(
                    action_type=row["action_type"],
                    file_path=row["file_path"],
                    line_number=row["line_number"],
                    old_content=row["old_content"],
                    new_content=row["new_content"],
                    timestamp=row["timestamp"],
                )
            return None

    def pop_undo_action(self) -> Optional[UndoAction]:
        """Get and remove the most recent undo action"""
        action = self.get_last_undo_action()
        if action:
            with self.cursor() as cur:
                cur.execute("""
                    DELETE FROM undo_history
                    WHERE id = (SELECT MAX(id) FROM undo_history)
                """)
        return action

    def clear_old_undo_actions(self, keep: int = 50) -> None:
        """Keep only the most recent N undo actions"""
        with self.cursor() as cur:
            cur.execute("""
                DELETE FROM undo_history
                WHERE id NOT IN (
                    SELECT id FROM undo_history ORDER BY id DESC LIMIT ?
                )
            """, (keep,))

    def _row_to_entry(self, row: sqlite3.Row) -> EntryRecord:
        """Convert database row to EntryRecord"""
        return EntryRecord(
            id=row["id"],
            entry_ref=row["entry_ref"],
            source_file=row["source_file"],
            line_number=row["line_number"],
            raw_line=row["raw_line"],
            entry_type=row["entry_type"],
            status=row["status"],
            signifier=row["signifier"],
            content=row["content"],
            entry_date=row["entry_date"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            collection=row["collection"],
            month=row["month"],
            migrated_to=row["migrated_to"],
            migrated_from=row["migrated_from"],
        )
