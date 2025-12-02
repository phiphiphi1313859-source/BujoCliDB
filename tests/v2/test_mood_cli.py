"""Tests for mood CLI commands."""

import pytest
from click.testing import CliRunner
from datetime import date

from clibujo_v2.cli import cli
from clibujo_v2.core.db import init_db
from clibujo_v2.core.mood import (
    get_mood_entry, get_medications, get_medication_by_name,
    get_current_episode, get_mood_triggers, get_all_targets,
)


@pytest.fixture
def runner(test_db_env):
    """Get CLI test runner."""
    init_db()
    return CliRunner()


class TestMoodCommands:
    """Tests for mood CLI commands."""

    def test_mood_quick(self, runner):
        """Quick mood entry."""
        result = runner.invoke(cli, ["mood", "quick", "2", "7", "7.5"])

        assert result.exit_code == 0
        assert "Logged" in result.output

        # Verify entry was created
        entry = get_mood_entry(date.today().isoformat())
        assert entry is not None
        assert entry.mood == 2
        assert entry.energy == 7
        assert entry.sleep_hours == 7.5

    def test_mood_add_dimensions(self, runner):
        """Add dimensions to mood entry."""
        result = runner.invoke(cli, ["mood", "add", "racing:3", "impulsivity:2"])

        assert result.exit_code == 0
        assert "Added" in result.output

        entry = get_mood_entry(date.today().isoformat())
        assert entry.racing_thoughts == 3
        assert entry.impulsivity == 2

    def test_mood_watch(self, runner):
        """Log watch data."""
        result = runner.invoke(cli, ["mood", "watch", "steps:8500", "rhr:62"])

        assert result.exit_code == 0
        assert "watch data" in result.output.lower()

    def test_mood_note(self, runner):
        """Add mood note."""
        result = runner.invoke(cli, ["mood", "note", "Feeling okay today"])

        assert result.exit_code == 0
        assert "Note saved" in result.output

        entry = get_mood_entry(date.today().isoformat())
        assert entry.note == "Feeling okay today"

    def test_mood_today(self, runner):
        """View today's mood."""
        # First add an entry
        runner.invoke(cli, ["mood", "quick", "1", "6", "7"])

        result = runner.invoke(cli, ["mood", "today"])

        assert result.exit_code == 0
        # Should show today's date

    def test_mood_week(self, runner):
        """View week mood summary."""
        result = runner.invoke(cli, ["mood", "week"])

        assert result.exit_code == 0
        assert "Week of" in result.output

    def test_mood_history(self, runner):
        """View mood history."""
        result = runner.invoke(cli, ["mood", "history"])

        assert result.exit_code == 0


class TestMedicationCommands:
    """Tests for medication CLI commands."""

    def test_meds_add(self, runner):
        """Add a medication."""
        result = runner.invoke(cli, ["mood", "meds", "add", "TestMed", "--dose", "100mg", "--time", "morning"])

        assert result.exit_code == 0
        assert "Added" in result.output

        med = get_medication_by_name("TestMed")
        assert med is not None
        assert med.dosage == "100mg"

    def test_meds_list(self, runner):
        """List medications."""
        runner.invoke(cli, ["mood", "meds", "add", "Med1"])
        runner.invoke(cli, ["mood", "meds", "add", "Med2"])

        result = runner.invoke(cli, ["mood", "meds", "list"])

        assert result.exit_code == 0
        assert "Med1" in result.output
        assert "Med2" in result.output

    def test_meds_remove(self, runner):
        """Remove (deactivate) a medication."""
        runner.invoke(cli, ["mood", "meds", "add", "OldMed"])

        result = runner.invoke(cli, ["mood", "meds", "remove", "OldMed"])

        assert result.exit_code == 0
        assert "Deactivated" in result.output

    def test_meds_log(self, runner):
        """Log medication taken."""
        runner.invoke(cli, ["mood", "meds", "add", "DailyMed"])

        result = runner.invoke(cli, ["mood", "meds", "log", "DailyMed"])

        assert result.exit_code == 0
        assert "taken" in result.output.lower()


class TestEpisodeCommands:
    """Tests for episode CLI commands."""

    def test_episode_start(self, runner):
        """Start tracking an episode."""
        result = runner.invoke(cli, ["mood", "episode", "start", "--type", "hypomania"])

        assert result.exit_code == 0
        assert "Started" in result.output

        current = get_current_episode()
        assert current is not None
        assert current.type == "hypomania"

    def test_episode_end(self, runner):
        """End an episode."""
        runner.invoke(cli, ["mood", "episode", "start", "--type", "depression"])

        result = runner.invoke(cli, ["mood", "episode", "end", "--note", "Feeling better"])

        assert result.exit_code == 0
        assert "Ended" in result.output

        current = get_current_episode()
        assert current is None  # No current episode

    def test_episode_list(self, runner):
        """List episodes."""
        runner.invoke(cli, ["mood", "episode", "add", "--start", "2024-11-01", "--end", "2024-11-10", "--type", "depression"])

        result = runner.invoke(cli, ["mood", "episode", "list"])

        assert result.exit_code == 0


class TestTriggerCommands:
    """Tests for trigger CLI commands."""

    def test_trigger_add(self, runner):
        """Add a custom trigger."""
        result = runner.invoke(cli, ["mood", "trigger", "add", "sleep < 5 for 2 days", "--warn", "Get more sleep!"])

        assert result.exit_code == 0
        assert "Added trigger" in result.output

        triggers = get_mood_triggers()
        assert len(triggers) == 1

    def test_trigger_list(self, runner):
        """List triggers."""
        # Must have a comparison operator to be valid
        runner.invoke(cli, ["mood", "trigger", "add", "sleep < 5", "--warn", "test warning"])

        result = runner.invoke(cli, ["mood", "trigger", "list"])

        assert result.exit_code == 0
        assert "sleep < 5" in result.output


class TestTargetCommands:
    """Tests for target CLI commands."""

    def test_target_set(self, runner):
        """Set a target."""
        result = runner.invoke(cli, ["mood", "target", "set", "sleep", "7.5"])

        assert result.exit_code == 0
        assert "target set" in result.output.lower()

        targets = get_all_targets()
        assert targets["sleep"] == 7.5

    def test_target_view(self, runner):
        """View targets."""
        runner.invoke(cli, ["mood", "target", "set", "sleep", "7.0"])
        runner.invoke(cli, ["mood", "target", "set", "steps", "8000"])

        result = runner.invoke(cli, ["mood", "target"])

        assert result.exit_code == 0
        assert "sleep" in result.output.lower()


class TestAnalysisCommands:
    """Tests for analysis CLI commands."""

    def test_mood_patterns(self, runner):
        """Check patterns."""
        result = runner.invoke(cli, ["mood", "patterns"])

        assert result.exit_code == 0

    def test_mood_correlate(self, runner):
        """Run correlation analysis."""
        result = runner.invoke(cli, ["mood", "correlate"])

        assert result.exit_code == 0

    def test_baseline_show(self, runner):
        """Show baselines."""
        result = runner.invoke(cli, ["mood", "baseline", "show"])

        assert result.exit_code == 0

    def test_baseline_recalculate(self, runner):
        """Recalculate baselines."""
        result = runner.invoke(cli, ["mood", "baseline", "recalculate"])

        assert result.exit_code == 0
        # Should say not enough data
