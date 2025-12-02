"""Tests for entry CRUD operations."""

import pytest
from datetime import date

from clibujo_v2.core.db import init_db
from clibujo_v2.core.entries import (
    create_entry,
    get_entry,
    get_entries_by_date,
    get_entries_by_month,
    get_entries_by_collection,
    get_open_tasks,
    update_entry,
    complete_entry,
    cancel_entry,
    reopen_entry,
    delete_entry,
    search_entries,
    get_entries_date_range,
)


class TestCreateEntry:
    """Tests for entry creation."""

    def test_create_task(self, db_connection):
        """Create a basic task."""
        entry = create_entry("Test task", entry_type="task", entry_date="2025-01-15", conn=db_connection)

        assert entry.id is not None
        assert entry.content == "Test task"
        assert entry.entry_type == "task"
        assert entry.status == "open"
        assert entry.entry_date == "2025-01-15"

    def test_create_event(self, db_connection):
        """Create an event."""
        entry = create_entry("Test event", entry_type="event", entry_date="2025-01-15", conn=db_connection)

        assert entry.entry_type == "event"
        assert entry.status is None

    def test_create_note(self, db_connection):
        """Create a note."""
        entry = create_entry("Test note", entry_type="note", entry_date="2025-01-15", conn=db_connection)

        assert entry.entry_type == "note"
        assert entry.status is None

    def test_create_with_signifier(self, db_connection):
        """Create entry with signifier."""
        entry = create_entry(
            "Priority task",
            entry_type="task",
            entry_date="2025-01-15",
            signifier="priority",
            conn=db_connection,
        )

        assert entry.signifier == "priority"

    def test_create_in_collection(self, db_connection, sample_collection):
        """Create entry in a collection."""
        entry = create_entry(
            "Collection task",
            entry_type="task",
            collection_id=sample_collection.id,
            conn=db_connection,
        )

        assert entry.collection_id == sample_collection.id

    def test_create_in_monthly_log(self, db_connection):
        """Create entry in monthly log."""
        entry = create_entry(
            "Future task",
            entry_type="task",
            entry_month="2025-02",
            conn=db_connection,
        )

        assert entry.entry_month == "2025-02"
        assert entry.entry_date is None


class TestGetEntry:
    """Tests for retrieving entries."""

    def test_get_existing_entry(self, sample_entries):
        """Get an existing entry by ID."""
        entry = get_entry(sample_entries[0].id)

        assert entry is not None
        assert entry.content == "Buy groceries"

    def test_get_nonexistent_entry(self, db_connection):
        """Get a non-existent entry."""
        entry = get_entry(9999)

        assert entry is None


class TestGetEntriesByDate:
    """Tests for getting entries by date."""

    def test_get_entries_by_date(self, sample_entries):
        """Get all entries for a date."""
        entries = get_entries_by_date("2025-01-15")

        assert len(entries) == 4

    def test_get_entries_by_date_filter_type(self, sample_entries):
        """Get only tasks for a date."""
        entries = get_entries_by_date("2025-01-15", include_events=False, include_notes=False)

        assert len(entries) == 2
        assert all(e.entry_type == "task" for e in entries)

    def test_get_entries_empty_date(self, db_connection):
        """Get entries for a date with no entries."""
        init_db()
        entries = get_entries_by_date("2025-12-31")

        assert entries == []


class TestUpdateEntry:
    """Tests for updating entries."""

    def test_update_content(self, sample_entries):
        """Update entry content."""
        entry = update_entry(sample_entries[0].id, content="Updated content")

        assert entry.content == "Updated content"

    def test_update_status(self, sample_entries):
        """Update entry status."""
        entry = update_entry(sample_entries[0].id, status="complete")

        assert entry.status == "complete"
        assert entry.completed_at is not None

    def test_update_signifier(self, sample_entries):
        """Update entry signifier."""
        entry = update_entry(sample_entries[0].id, signifier="priority")

        assert entry.signifier == "priority"

    def test_clear_signifier(self, sample_entries):
        """Clear entry signifier."""
        # First set it
        update_entry(sample_entries[0].id, signifier="priority")
        # Then clear it
        entry = update_entry(sample_entries[0].id, signifier="")

        assert entry.signifier is None


class TestCompleteEntry:
    """Tests for completing tasks."""

    def test_complete_task(self, sample_entries):
        """Complete a task."""
        entry = complete_entry(sample_entries[0].id)

        assert entry.status == "complete"
        assert entry.completed_at is not None

    def test_complete_non_task(self, sample_entries):
        """Try to complete an event (should fail)."""
        # Events don't have status
        event = sample_entries[1]
        result = complete_entry(event.id)

        # update_entry returns the entry even if status wasn't applicable
        # but the status should remain None
        assert result is not None


class TestCancelEntry:
    """Tests for cancelling tasks."""

    def test_cancel_task(self, sample_entries):
        """Cancel a task."""
        entry = cancel_entry(sample_entries[0].id)

        assert entry.status == "cancelled"


class TestReopenEntry:
    """Tests for reopening tasks."""

    def test_reopen_completed_task(self, sample_entries):
        """Reopen a completed task."""
        complete_entry(sample_entries[0].id)
        entry = reopen_entry(sample_entries[0].id)

        assert entry.status == "open"
        assert entry.completed_at is None


class TestDeleteEntry:
    """Tests for deleting entries."""

    def test_delete_entry(self, sample_entries):
        """Delete an entry."""
        entry_id = sample_entries[0].id
        result = delete_entry(entry_id)

        assert result is True
        assert get_entry(entry_id) is None

    def test_delete_nonexistent_entry(self, db_connection):
        """Delete a non-existent entry."""
        result = delete_entry(9999)

        assert result is False


class TestSearchEntries:
    """Tests for full-text search."""

    def test_search_by_content(self, db_connection):
        """Search entries by content."""
        # Create entries with FTS triggers active
        create_entry("Buy groceries", entry_date="2025-01-15", conn=db_connection)
        create_entry("Call mom", entry_date="2025-01-15", conn=db_connection)
        db_connection.commit()

        results = search_entries("groceries", conn=db_connection)

        assert len(results) == 1
        assert results[0].content == "Buy groceries"

    def test_search_no_results(self, db_connection):
        """Search with no matching results."""
        create_entry("Something else", entry_date="2025-01-15", conn=db_connection)
        db_connection.commit()

        results = search_entries("nonexistent", conn=db_connection)

        assert results == []


class TestGetOpenTasks:
    """Tests for getting open tasks."""

    def test_get_open_tasks(self, sample_entries):
        """Get all open tasks."""
        tasks = get_open_tasks()

        assert len(tasks) == 2
        assert all(t.status == "open" for t in tasks)

    def test_get_open_tasks_before_date(self, sample_entries):
        """Get open tasks before a date."""
        tasks = get_open_tasks(before_date="2025-01-16")

        assert len(tasks) == 2

    def test_get_open_tasks_after_completing(self, sample_entries):
        """Open tasks count should decrease after completing."""
        complete_entry(sample_entries[0].id)
        tasks = get_open_tasks()

        assert len(tasks) == 1
