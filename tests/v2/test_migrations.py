"""Tests for task migration operations."""

import pytest
from datetime import date

from clibujo_v2.core.entries import create_entry, get_entry
from clibujo_v2.core.collections import create_collection
from clibujo_v2.core.migrations import (
    migrate_to_date,
    migrate_to_month,
    migrate_to_collection,
    migrate_forward,
    get_migration_history,
    get_tasks_needing_migration,
    bulk_migrate_to_today,
)


class TestMigrateToDate:
    """Tests for migrating tasks to a specific date."""

    def test_migrate_to_date(self, db_connection):
        """Migrate a task to a new date."""
        # Create original task
        original = create_entry(
            "Test task",
            entry_type="task",
            entry_date="2025-01-10",
            conn=db_connection,
        )

        # Migrate to new date
        new_entry = migrate_to_date(original.id, "2025-01-15", conn=db_connection)

        assert new_entry is not None
        assert new_entry.content == "Test task"
        assert new_entry.entry_date == "2025-01-15"
        assert new_entry.status == "open"

        # Original should be marked migrated
        original = get_entry(original.id, conn=db_connection)
        assert original.status == "migrated"

    def test_migrate_preserves_signifier(self, db_connection):
        """Migration preserves signifier."""
        original = create_entry(
            "Priority task",
            entry_type="task",
            entry_date="2025-01-10",
            signifier="priority",
            conn=db_connection,
        )

        new_entry = migrate_to_date(original.id, "2025-01-15", conn=db_connection)

        assert new_entry.signifier == "priority"

    def test_cannot_migrate_completed_task(self, db_connection):
        """Cannot migrate a completed task."""
        task = create_entry(
            "Completed task",
            entry_type="task",
            entry_date="2025-01-10",
            status="complete",
            conn=db_connection,
        )

        result = migrate_to_date(task.id, "2025-01-15", conn=db_connection)

        assert result is None

    def test_cannot_migrate_event(self, db_connection):
        """Cannot migrate an event."""
        event = create_entry(
            "Test event",
            entry_type="event",
            entry_date="2025-01-10",
            conn=db_connection,
        )

        result = migrate_to_date(event.id, "2025-01-15", conn=db_connection)

        assert result is None


class TestMigrateToMonth:
    """Tests for scheduling tasks to a future month."""

    def test_migrate_to_month(self, db_connection):
        """Schedule a task for a future month."""
        original = create_entry(
            "Future task",
            entry_type="task",
            entry_date="2025-01-10",
            conn=db_connection,
        )

        new_entry = migrate_to_month(original.id, "2025-03", conn=db_connection)

        assert new_entry is not None
        assert new_entry.entry_month == "2025-03"
        assert new_entry.entry_date is None

        # Original should be marked scheduled
        original = get_entry(original.id, conn=db_connection)
        assert original.status == "scheduled"


class TestMigrateToCollection:
    """Tests for migrating tasks to collections."""

    def test_migrate_to_collection(self, db_connection):
        """Migrate a task to a collection."""
        collection = create_collection("Test Project", conn=db_connection)
        original = create_entry(
            "Project task",
            entry_type="task",
            entry_date="2025-01-10",
            conn=db_connection,
        )

        new_entry = migrate_to_collection(original.id, collection.id, conn=db_connection)

        assert new_entry is not None
        assert new_entry.collection_id == collection.id
        assert new_entry.entry_date is None

        # Original should be marked migrated
        original = get_entry(original.id, conn=db_connection)
        assert original.status == "migrated"


class TestMigrateForward:
    """Tests for migrating tasks to today."""

    def test_migrate_forward(self, db_connection):
        """Migrate a task to today."""
        original = create_entry(
            "Old task",
            entry_type="task",
            entry_date="2025-01-01",
            conn=db_connection,
        )

        new_entry = migrate_forward(original.id, conn=db_connection)
        today = date.today().isoformat()

        assert new_entry is not None
        assert new_entry.entry_date == today


class TestMigrationHistory:
    """Tests for migration history tracking."""

    def test_migration_history(self, db_connection):
        """Track migration history."""
        original = create_entry(
            "Task with history",
            entry_type="task",
            entry_date="2025-01-01",
            conn=db_connection,
        )

        migrate_to_date(original.id, "2025-01-05", conn=db_connection)

        history = get_migration_history(original.id, conn=db_connection)

        assert len(history) == 1
        assert history[0].from_date == "2025-01-01"
        assert history[0].to_date == "2025-01-05"


class TestGetTasksNeedingMigration:
    """Tests for finding tasks that need migration."""

    def test_old_open_tasks_need_migration(self, db_connection):
        """Open tasks from past dates need migration."""
        create_entry(
            "Old task",
            entry_type="task",
            entry_date="2025-01-01",
            conn=db_connection,
        )
        create_entry(
            "New task",
            entry_type="task",
            entry_date="2025-01-15",
            conn=db_connection,
        )

        tasks = get_tasks_needing_migration("2025-01-10", conn=db_connection)

        assert len(tasks) == 1
        assert tasks[0].content == "Old task"

    def test_completed_tasks_not_needing_migration(self, db_connection):
        """Completed tasks don't need migration."""
        create_entry(
            "Completed task",
            entry_type="task",
            entry_date="2025-01-01",
            status="complete",
            conn=db_connection,
        )

        tasks = get_tasks_needing_migration("2025-01-10", conn=db_connection)

        assert len(tasks) == 0


class TestBulkMigration:
    """Tests for bulk migration."""

    def test_bulk_migrate_to_today(self, db_connection):
        """Migrate multiple tasks to today."""
        task1 = create_entry(
            "Task 1",
            entry_type="task",
            entry_date="2025-01-01",
            conn=db_connection,
        )
        task2 = create_entry(
            "Task 2",
            entry_type="task",
            entry_date="2025-01-02",
            conn=db_connection,
        )

        new_entries = bulk_migrate_to_today([task1.id, task2.id], conn=db_connection)

        assert len(new_entries) == 2

        today = date.today().isoformat()
        assert all(e.entry_date == today for e in new_entries)
