"""Tests for the database module"""

import pytest
import tempfile
from datetime import date, datetime
from pathlib import Path

from clibujo.core.database import Database
from clibujo.core.models import UndoAction


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.init_schema()
        yield db
        db.close()


class TestDatabase:
    """Tests for Database class"""

    def test_init_schema(self, temp_db):
        """Test that schema is created correctly"""
        # Should not raise
        with temp_db.cursor() as cur:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row["name"] for row in cur.fetchall()}

        assert "entries" in tables
        assert "entries_fts" in tables
        assert "file_hashes" in tables
        assert "undo_history" in tables

    def test_insert_and_get_entry(self, temp_db):
        """Test inserting and retrieving an entry"""
        entry_id = temp_db.insert_entry(
            entry_ref="abc123",
            source_file="daily/2024-12-03.md",
            line_number=5,
            raw_line="[ ] Test task",
            entry_type="task",
            content="Test task",
            status="open",
            entry_date=date(2024, 12, 3),
        )

        assert entry_id > 0

        entry = temp_db.get_entry_by_ref("abc123")
        assert entry is not None
        assert entry.content == "Test task"
        assert entry.entry_type == "task"
        assert entry.status == "open"

    def test_get_entry_by_prefix(self, temp_db):
        """Test getting entry by ref prefix"""
        temp_db.insert_entry(
            entry_ref="abc123",
            source_file="daily/2024-12-03.md",
            line_number=5,
            raw_line="[ ] Test",
            entry_type="task",
            content="Test",
        )

        entry = temp_db.get_entry_by_ref_prefix("abc")
        assert entry is not None
        assert entry.entry_ref == "abc123"

    def test_get_entries_by_date(self, temp_db):
        """Test getting entries by date"""
        target_date = date(2024, 12, 3)

        temp_db.insert_entry(
            entry_ref="ref1",
            source_file="daily/2024-12-03.md",
            line_number=1,
            raw_line="[ ] Task 1",
            entry_type="task",
            content="Task 1",
            entry_date=target_date,
        )
        temp_db.insert_entry(
            entry_ref="ref2",
            source_file="daily/2024-12-03.md",
            line_number=2,
            raw_line="[ ] Task 2",
            entry_type="task",
            content="Task 2",
            entry_date=target_date,
        )

        entries = temp_db.get_entries_by_date(target_date)
        assert len(entries) == 2

    def test_search(self, temp_db):
        """Test full-text search"""
        temp_db.insert_entry(
            entry_ref="ref1",
            source_file="daily/2024-12-03.md",
            line_number=1,
            raw_line="[ ] Buy groceries",
            entry_type="task",
            content="Buy groceries",
        )
        temp_db.insert_entry(
            entry_ref="ref2",
            source_file="daily/2024-12-03.md",
            line_number=2,
            raw_line="[ ] Call mom",
            entry_type="task",
            content="Call mom",
        )

        results = temp_db.search("groceries")
        assert len(results) == 1
        entry, snippet = results[0]
        assert "groceries" in entry.content.lower()

    def test_file_hash(self, temp_db):
        """Test file hash storage and retrieval"""
        file_path = "daily/2024-12-03.md"
        hash_value = "abc123hash"

        temp_db.set_file_hash(file_path, hash_value)
        retrieved = temp_db.get_file_hash(file_path)
        assert retrieved == hash_value

    def test_undo_action(self, temp_db):
        """Test undo action storage"""
        action = UndoAction(
            action_type="edit",
            file_path="/path/to/file.md",
            line_number=5,
            old_content="old",
            new_content="new",
        )

        temp_db.add_undo_action(action)
        retrieved = temp_db.get_last_undo_action()

        assert retrieved is not None
        assert retrieved.action_type == "edit"
        assert retrieved.old_content == "old"

    def test_pop_undo_action(self, temp_db):
        """Test popping undo action"""
        action = UndoAction(
            action_type="edit",
            file_path="/path/to/file.md",
            line_number=5,
            old_content="old",
            new_content="new",
        )

        temp_db.add_undo_action(action)
        popped = temp_db.pop_undo_action()

        assert popped is not None
        assert temp_db.get_last_undo_action() is None

    def test_get_stats(self, temp_db):
        """Test statistics retrieval"""
        # Add some tasks
        for i in range(5):
            temp_db.insert_entry(
                entry_ref=f"ref{i}",
                source_file="daily/2024-12-03.md",
                line_number=i + 1,
                raw_line=f"[ ] Task {i}",
                entry_type="task",
                content=f"Task {i}",
                status="complete" if i < 3 else "open",
                entry_date=date(2024, 12, 3),
            )

        stats = temp_db.get_stats(year=2024)

        assert stats["overall"]["total"] == 5
        assert stats["overall"]["completed"] == 3
        assert stats["overall"]["open"] == 2
