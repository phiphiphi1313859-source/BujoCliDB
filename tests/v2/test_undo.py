"""Tests for undo system."""

import pytest

from clibujo_v2.core.entries import create_entry, get_entry, update_entry, delete_entry
from clibujo_v2.core.undo import (
    get_undo_history,
    get_last_action,
    undo_last_action,
    undo_multiple,
    clear_undo_history,
    describe_action,
)


class TestUndoHistory:
    """Tests for undo history."""

    def test_entry_create_recorded(self, db_connection):
        """Entry creation is recorded in undo history."""
        create_entry("Test task", entry_date="2025-01-15", conn=db_connection)

        history = get_undo_history(conn=db_connection)

        assert len(history) >= 1
        assert history[0].action_type == "create"
        assert history[0].table_name == "entries"

    def test_entry_update_recorded(self, db_connection):
        """Entry update is recorded in undo history."""
        entry = create_entry("Test task", entry_date="2025-01-15", conn=db_connection)
        update_entry(entry.id, content="Updated content", conn=db_connection)

        history = get_undo_history(conn=db_connection)

        # Should have create and update
        assert len(history) >= 2
        assert history[0].action_type == "update"

    def test_entry_delete_recorded(self, db_connection):
        """Entry deletion is recorded in undo history."""
        entry = create_entry("Test task", entry_date="2025-01-15", conn=db_connection)
        delete_entry(entry.id, conn=db_connection)

        history = get_undo_history(conn=db_connection)

        assert history[0].action_type == "delete"


class TestGetLastAction:
    """Tests for getting last action."""

    def test_get_last_action(self, db_connection):
        """Get the most recent action."""
        create_entry("Task 1", entry_date="2025-01-15", conn=db_connection)
        create_entry("Task 2", entry_date="2025-01-15", conn=db_connection)

        last = get_last_action(conn=db_connection)

        assert last is not None
        assert last.action_type == "create"


class TestUndoLastAction:
    """Tests for undoing last action."""

    def test_undo_create(self, db_connection):
        """Undo entry creation."""
        entry = create_entry("Test task", entry_date="2025-01-15", conn=db_connection)
        entry_id = entry.id

        result = undo_last_action(conn=db_connection)

        assert result["success"] is True
        assert "Deleted" in result["message"]

        # Entry should be gone
        assert get_entry(entry_id, conn=db_connection) is None

    def test_undo_update(self, db_connection):
        """Undo entry update."""
        entry = create_entry("Original content", entry_date="2025-01-15", conn=db_connection)
        update_entry(entry.id, content="Updated content", conn=db_connection)

        result = undo_last_action(conn=db_connection)

        assert result["success"] is True

        # Content should be restored
        entry = get_entry(entry.id, conn=db_connection)
        assert entry.content == "Original content"

    def test_undo_delete(self, db_connection):
        """Undo entry deletion."""
        entry = create_entry("Test task", entry_date="2025-01-15", conn=db_connection)
        entry_id = entry.id
        delete_entry(entry_id, conn=db_connection)

        result = undo_last_action(conn=db_connection)

        assert result["success"] is True
        assert "Restored" in result["message"]

    def test_undo_nothing(self, db_connection):
        """Undo with empty history."""
        # Clear any existing history
        clear_undo_history(conn=db_connection)

        result = undo_last_action(conn=db_connection)

        assert result["success"] is False
        assert "Nothing to undo" in result["message"]


class TestUndoMultiple:
    """Tests for undoing multiple actions."""

    def test_undo_multiple(self, db_connection):
        """Undo multiple actions."""
        create_entry("Task 1", entry_date="2025-01-15", conn=db_connection)
        create_entry("Task 2", entry_date="2025-01-15", conn=db_connection)
        create_entry("Task 3", entry_date="2025-01-15", conn=db_connection)

        results = undo_multiple(2, conn=db_connection)

        assert len(results) == 2


class TestClearUndoHistory:
    """Tests for clearing undo history."""

    def test_clear_history(self, db_connection):
        """Clear all undo history."""
        create_entry("Test", entry_date="2025-01-15", conn=db_connection)
        create_entry("Test 2", entry_date="2025-01-15", conn=db_connection)

        count = clear_undo_history(conn=db_connection)

        assert count >= 2

        history = get_undo_history(conn=db_connection)
        assert len(history) == 0


class TestDescribeAction:
    """Tests for action descriptions."""

    def test_describe_create(self, db_connection):
        """Describe a create action."""
        create_entry("Test task", entry_date="2025-01-15", conn=db_connection)

        action = get_last_action(conn=db_connection)
        description = describe_action(action)

        assert "Created" in description
        assert "entry" in description.lower()
        assert "Test task" in description

    def test_describe_truncates_long_content(self, db_connection):
        """Long content is truncated in description."""
        long_content = "A" * 100
        create_entry(long_content, entry_date="2025-01-15", conn=db_connection)

        action = get_last_action(conn=db_connection)
        description = describe_action(action)

        assert len(description) < 100
        assert "..." in description
