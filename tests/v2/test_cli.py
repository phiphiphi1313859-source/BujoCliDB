"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner

from clibujo_v2.cli import cli
from clibujo_v2.core.db import init_db
from clibujo_v2.core.entries import get_entries_by_date


@pytest.fixture
def runner(test_db_env):
    """Get CLI test runner."""
    init_db()
    return CliRunner()


class TestBasicCommands:
    """Tests for basic CLI commands."""

    def test_version(self, runner):
        """Show version."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "CLIBuJo" in result.output

    def test_init(self, runner):
        """Initialize database."""
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "initialized" in result.output.lower()

    def test_today_empty(self, runner):
        """View today with no entries."""
        result = runner.invoke(cli, ["today"])

        assert result.exit_code == 0
        # Should show the date header at minimum


class TestAddCommand:
    """Tests for add command."""

    def test_add_task(self, runner):
        """Add a basic task."""
        result = runner.invoke(cli, ["add", "Test", "task"])

        assert result.exit_code == 0
        assert "Added" in result.output
        assert "Test task" in result.output

    def test_add_with_priority(self, runner):
        """Add a priority task."""
        result = runner.invoke(cli, ["add", "-p", "Priority", "task"])

        assert result.exit_code == 0
        assert "*" in result.output  # Priority signifier

    def test_add_event(self, runner):
        """Add an event."""
        result = runner.invoke(cli, ["add", "-t", "event", "Meeting at 2pm"])

        assert result.exit_code == 0
        assert "Meeting at 2pm" in result.output


class TestEntriesCommands:
    """Tests for entries subcommands."""

    def test_entries_view(self, runner):
        """View entries for a date."""
        runner.invoke(cli, ["add", "Test task"])
        result = runner.invoke(cli, ["entries", "view", "today"])

        assert result.exit_code == 0

    def test_entries_complete(self, runner):
        """Complete a task."""
        # First add a task
        runner.invoke(cli, ["add", "Task to complete"])

        # Get the entry ID from the output
        from clibujo_v2.core.entries import get_entries_by_date
        from datetime import date
        entries = get_entries_by_date(date.today().isoformat())
        entry_id = entries[0].id

        result = runner.invoke(cli, ["entries", "complete", str(entry_id)])

        assert result.exit_code == 0
        assert "Completed" in result.output

    def test_entries_search(self, runner):
        """Search entries."""
        runner.invoke(cli, ["add", "Buy groceries"])
        runner.invoke(cli, ["add", "Call mom"])

        result = runner.invoke(cli, ["entries", "search", "groceries"])

        assert result.exit_code == 0
        assert "groceries" in result.output


class TestCollectionsCommands:
    """Tests for collections subcommands."""

    def test_collections_create(self, runner):
        """Create a collection."""
        result = runner.invoke(cli, ["collections", "create", "Test Project"])

        assert result.exit_code == 0
        assert "Created" in result.output

    def test_collections_list(self, runner):
        """List collections."""
        runner.invoke(cli, ["collections", "create", "Project 1"])
        runner.invoke(cli, ["collections", "create", "Project 2"])

        result = runner.invoke(cli, ["collections", "list"])

        assert result.exit_code == 0
        assert "Project 1" in result.output
        assert "Project 2" in result.output

    def test_collections_view(self, runner):
        """View a collection."""
        runner.invoke(cli, ["collections", "create", "My Project"])

        result = runner.invoke(cli, ["collections", "view", "My Project"])

        assert result.exit_code == 0
        assert "My Project" in result.output


class TestHabitsCommands:
    """Tests for habits subcommands."""

    def test_habits_add(self, runner):
        """Add a habit."""
        result = runner.invoke(cli, ["habits", "add", "Exercise"])

        assert result.exit_code == 0
        assert "Created" in result.output

    def test_habits_list(self, runner):
        """List habits."""
        runner.invoke(cli, ["habits", "add", "Exercise"])
        runner.invoke(cli, ["habits", "add", "Read"])

        result = runner.invoke(cli, ["habits", "list"])

        assert result.exit_code == 0
        assert "Exercise" in result.output
        assert "Read" in result.output

    def test_habits_done(self, runner):
        """Mark habit as done."""
        runner.invoke(cli, ["habits", "add", "Exercise"])

        result = runner.invoke(cli, ["habits", "done", "Exercise"])

        assert result.exit_code == 0
        assert "done" in result.output.lower() or "Marked" in result.output


class TestMigrateCommands:
    """Tests for migrate subcommands."""

    def test_migrate_review(self, runner):
        """Review tasks for migration."""
        result = runner.invoke(cli, ["migrate", "review"])

        assert result.exit_code == 0


class TestUndoCommand:
    """Tests for undo command."""

    def test_undo(self, runner):
        """Undo last action."""
        runner.invoke(cli, ["add", "Task to undo"])

        result = runner.invoke(cli, ["undo"])

        assert result.exit_code == 0
        # Should either say undone or nothing to undo


class TestDoneShortcut:
    """Tests for done shortcut command."""

    def test_done_task(self, runner):
        """Mark task done by ID."""
        runner.invoke(cli, ["add", "Task"])

        from clibujo_v2.core.entries import get_entries_by_date
        from datetime import date
        entries = get_entries_by_date(date.today().isoformat())
        entry_id = entries[0].id

        result = runner.invoke(cli, ["done", str(entry_id)])

        assert result.exit_code == 0
        assert "Completed" in result.output

    def test_done_habit(self, runner):
        """Mark habit done by name."""
        runner.invoke(cli, ["habits", "add", "Exercise"])

        result = runner.invoke(cli, ["done", "Exercise"])

        assert result.exit_code == 0
