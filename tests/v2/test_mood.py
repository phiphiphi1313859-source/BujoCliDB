"""Tests for mood tracking integration."""

import pytest
from datetime import date, timedelta

from clibujo_v2.core.db import init_db
from clibujo_v2.core.mood import (
    MoodEntry, WatchData, Medication, Episode, MoodTrigger, Baseline,
    get_mood_entry, save_mood_entry, undo_mood_entry,
    get_mood_entries, get_recent_mood_entries,
    get_watch_data, save_watch_data,
    get_medications, get_medication_by_name, add_medication,
    deactivate_medication, log_medication, get_med_logs_for_date,
    get_current_episode, start_episode, end_episode, add_episode, get_episodes,
    get_mood_triggers, add_mood_trigger, set_mood_trigger_active, delete_mood_trigger,
    get_baseline, get_all_baselines, save_baseline,
    get_target, get_all_targets, set_target,
)


class TestMoodEntry:
    """Tests for mood entry CRUD operations."""

    def test_create_mood_entry(self, db_connection):
        """Create a basic mood entry."""
        entry = MoodEntry(
            date="2025-01-15",
            mood=2,
            energy=7,
            sleep_hours=7.5,
        )
        saved = save_mood_entry(entry, conn=db_connection)

        assert saved.id is not None
        assert saved.mood == 2
        assert saved.energy == 7
        assert saved.sleep_hours == 7.5

    def test_get_mood_entry(self, db_connection):
        """Retrieve a mood entry by date."""
        entry = MoodEntry(date="2025-01-15", mood=1)
        save_mood_entry(entry, conn=db_connection)

        retrieved = get_mood_entry("2025-01-15", conn=db_connection)

        assert retrieved is not None
        assert retrieved.mood == 1

    def test_get_nonexistent_mood_entry(self, db_connection):
        """Get a non-existent mood entry returns None."""
        init_db()
        result = get_mood_entry("2099-12-31", conn=db_connection)

        assert result is None

    def test_update_mood_entry(self, db_connection):
        """Update an existing mood entry."""
        entry = MoodEntry(date="2025-01-15", mood=1, energy=5)
        save_mood_entry(entry, conn=db_connection)

        # Update with new values
        update = MoodEntry(date="2025-01-15", mood=3, anxiety=2)
        save_mood_entry(update, conn=db_connection)

        retrieved = get_mood_entry("2025-01-15", conn=db_connection)
        assert retrieved.mood == 3
        assert retrieved.energy == 5  # Should be preserved
        assert retrieved.anxiety == 2

    def test_mood_entry_with_all_fields(self, db_connection):
        """Create mood entry with all fields."""
        entry = MoodEntry(
            date="2025-01-15",
            mood=-2,
            energy=4,
            sleep_hours=6.0,
            sleep_quality=3,
            irritability=3,
            anxiety=4,
            racing_thoughts=2,
            impulsivity=1,
            concentration=2,
            social_drive=-1,
            appetite=0,
            note="Tough day",
        )
        saved = save_mood_entry(entry, conn=db_connection)

        retrieved = get_mood_entry("2025-01-15", conn=db_connection)
        assert retrieved.mood == -2
        assert retrieved.energy == 4
        assert retrieved.irritability == 3
        assert retrieved.racing_thoughts == 2
        assert retrieved.social_drive == -1
        assert retrieved.note == "Tough day"


class TestMoodEntryRange:
    """Tests for getting mood entries by date range."""

    def test_get_mood_entries(self, db_connection):
        """Get entries in a date range."""
        for i in range(5):
            entry = MoodEntry(date=f"2025-01-{10+i:02d}", mood=i-2)
            save_mood_entry(entry, conn=db_connection)

        entries = get_mood_entries("2025-01-10", "2025-01-14", conn=db_connection)

        assert len(entries) == 5
        assert entries[0].date == "2025-01-10"
        assert entries[4].date == "2025-01-14"

    def test_get_recent_mood_entries(self, db_connection):
        """Get recent N days of entries."""
        for i in range(10):
            entry = MoodEntry(date=f"2025-01-{10+i:02d}", mood=0)
            save_mood_entry(entry, conn=db_connection)

        entries = get_recent_mood_entries(5, conn=db_connection)

        assert len(entries) == 5


class TestWatchData:
    """Tests for watch/fitness data."""

    def test_save_watch_data(self, db_connection):
        """Save watch data."""
        data = WatchData(date="2025-01-15", steps=8500, resting_hr=62, hrv=45)
        saved = save_watch_data(data, conn=db_connection)

        assert saved.id is not None
        assert saved.steps == 8500

    def test_get_watch_data(self, db_connection):
        """Retrieve watch data."""
        data = WatchData(date="2025-01-15", steps=10000)
        save_watch_data(data, conn=db_connection)

        retrieved = get_watch_data("2025-01-15", conn=db_connection)

        assert retrieved is not None
        assert retrieved.steps == 10000

    def test_update_watch_data(self, db_connection):
        """Update existing watch data."""
        data = WatchData(date="2025-01-15", steps=8000)
        save_watch_data(data, conn=db_connection)

        # Update with hrv
        update = WatchData(date="2025-01-15", hrv=50)
        save_watch_data(update, conn=db_connection)

        retrieved = get_watch_data("2025-01-15", conn=db_connection)
        assert retrieved.steps == 8000  # Preserved
        assert retrieved.hrv == 50  # Added


class TestMedications:
    """Tests for medication tracking."""

    def test_add_medication(self, db_connection):
        """Add a new medication."""
        med = Medication(name="TestMed", dosage="100mg", time_of_day="morning")
        saved = add_medication(med, conn=db_connection)

        assert saved.id is not None
        assert saved.name == "TestMed"

    def test_get_medication_by_name(self, db_connection):
        """Get medication by name (case-insensitive)."""
        med = Medication(name="LithiumCarb", dosage="300mg")
        add_medication(med, conn=db_connection)

        retrieved = get_medication_by_name("lithiumcarb", conn=db_connection)

        assert retrieved is not None
        assert retrieved.dosage == "300mg"

    def test_deactivate_medication(self, db_connection):
        """Deactivate a medication."""
        med = Medication(name="OldMed")
        add_medication(med, conn=db_connection)

        result = deactivate_medication("OldMed", conn=db_connection)

        assert result is True
        meds = get_medications(active_only=True, conn=db_connection)
        assert len(meds) == 0

    def test_log_medication(self, db_connection):
        """Log medication taken."""
        med = Medication(name="DailyMed")
        saved = add_medication(med, conn=db_connection)

        log = log_medication(saved.id, "2025-01-15", taken=True, time_taken="08:00", conn=db_connection)

        assert log.taken is True
        assert log.time_taken == "08:00"

    def test_get_med_logs_for_date(self, db_connection):
        """Get medication logs for a date."""
        med1 = Medication(name="Med1", time_of_day="morning")
        med2 = Medication(name="Med2", time_of_day="evening")
        saved1 = add_medication(med1, conn=db_connection)
        add_medication(med2, conn=db_connection)

        log_medication(saved1.id, "2025-01-15", taken=True, conn=db_connection)

        logs = get_med_logs_for_date("2025-01-15", conn=db_connection)

        assert len(logs) == 2
        # Note: taken comes back as 1/0/None from SQLite, not True/False
        assert any(log["name"] == "Med1" and log["taken"] == 1 for log in logs)
        assert any(log["name"] == "Med2" and log["taken"] is None for log in logs)


class TestEpisodes:
    """Tests for episode tracking."""

    def test_start_episode(self, db_connection):
        """Start a new episode."""
        ep = start_episode("hypomania", "2025-01-10", severity=3, conn=db_connection)

        assert ep.id is not None
        assert ep.type == "hypomania"
        assert ep.severity == 3

    def test_end_episode(self, db_connection):
        """End an episode."""
        ep = start_episode("depression", "2025-01-01", conn=db_connection)
        ended = end_episode(ep.id, "2025-01-15", "Feeling better", conn=db_connection)

        assert ended.end_date == "2025-01-15"
        assert ended.note == "Feeling better"

    def test_get_current_episode(self, db_connection):
        """Get current open episode."""
        init_db()
        start_episode("mania", conn=db_connection)

        current = get_current_episode(conn=db_connection)

        assert current is not None
        assert current.type == "mania"
        assert current.end_date is None

    def test_add_past_episode(self, db_connection):
        """Add a past episode with dates."""
        ep = add_episode(
            "2024-06-01", "2024-06-20", "mixed",
            severity=4, note="Difficult period",
            conn=db_connection
        )

        assert ep.start_date == "2024-06-01"
        assert ep.end_date == "2024-06-20"
        assert ep.type == "mixed"

    def test_get_episodes(self, db_connection):
        """Get episodes from recent months."""
        # Use recent dates that will definitely be within 12 months
        from datetime import date, timedelta
        recent = date.today() - timedelta(days=30)
        recent2 = date.today() - timedelta(days=60)
        add_episode(recent2.isoformat(), (recent2 + timedelta(days=10)).isoformat(), "depression", conn=db_connection)
        add_episode(recent.isoformat(), (recent + timedelta(days=5)).isoformat(), "hypomania", conn=db_connection)

        episodes = get_episodes(12, conn=db_connection)

        assert len(episodes) >= 2


class TestMoodTriggers:
    """Tests for custom trigger definitions."""

    def test_add_trigger(self, db_connection):
        """Add a custom trigger."""
        trig = add_mood_trigger("sleep < 5 for 2 days", "Get more sleep!", conn=db_connection)

        assert trig.id is not None
        assert trig.condition == "sleep < 5 for 2 days"
        assert trig.message == "Get more sleep!"
        assert trig.active is True

    def test_disable_trigger(self, db_connection):
        """Disable a trigger."""
        trig = add_mood_trigger("mood < -3", "Check in with therapist", conn=db_connection)
        set_mood_trigger_active(trig.id, False, conn=db_connection)

        triggers = get_mood_triggers(active_only=True, conn=db_connection)

        assert len(triggers) == 0

    def test_delete_trigger(self, db_connection):
        """Delete a trigger."""
        trig = add_mood_trigger("test", "test message", conn=db_connection)
        result = delete_mood_trigger(trig.id, conn=db_connection)

        assert result is True
        triggers = get_mood_triggers(active_only=False, conn=db_connection)
        assert len(triggers) == 0


class TestBaselines:
    """Tests for baseline calculations."""

    def test_save_and_get_baseline(self, db_connection):
        """Save and retrieve a baseline."""
        baseline = Baseline(
            metric="mood",
            value=1.5,
            std_dev=2.1,
            calculated_at="2025-01-15T10:00:00",
            days_used=30,
        )
        save_baseline(baseline, conn=db_connection)

        retrieved = get_baseline("mood", conn=db_connection)

        assert retrieved is not None
        assert retrieved.value == 1.5
        assert retrieved.std_dev == 2.1

    def test_get_all_baselines(self, db_connection):
        """Get all baselines."""
        save_baseline(Baseline("mood", 1.0, 2.0, "2025-01-01", 30), conn=db_connection)
        save_baseline(Baseline("energy", 6.5, 1.5, "2025-01-01", 30), conn=db_connection)

        baselines = get_all_baselines(conn=db_connection)

        assert len(baselines) == 2


class TestTargets:
    """Tests for target setting."""

    def test_set_and_get_target(self, db_connection):
        """Set and retrieve a target."""
        set_target("sleep", 7.5, conn=db_connection)

        value = get_target("sleep", conn=db_connection)

        assert value == 7.5

    def test_get_all_targets(self, db_connection):
        """Get all targets."""
        set_target("sleep", 7.0, conn=db_connection)
        set_target("steps", 8000, conn=db_connection)

        targets = get_all_targets(conn=db_connection)

        assert targets["sleep"] == 7.0
        assert targets["steps"] == 8000


class TestMoodUndo:
    """Tests for mood entry undo."""

    def test_undo_mood_entry(self, db_connection):
        """Undo changes to a mood entry."""
        # Create initial entry
        entry = MoodEntry(date="2025-01-15", mood=2, energy=6)
        save_mood_entry(entry, conn=db_connection)

        # Update it
        update = MoodEntry(date="2025-01-15", mood=-1, energy=3)
        save_mood_entry(update, conn=db_connection)

        # Undo
        restored = undo_mood_entry("2025-01-15", conn=db_connection)

        assert restored is not None
        assert restored.mood == 2
        assert restored.energy == 6

    def test_undo_no_history(self, db_connection):
        """Undo with no history returns None."""
        init_db()
        result = undo_mood_entry("2025-01-15", conn=db_connection)

        assert result is None
