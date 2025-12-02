"""Tests for habit tracking operations."""

import pytest
from datetime import date, timedelta

from clibujo_v2.core.habits import (
    create_habit,
    get_habit,
    get_habit_by_name,
    get_all_habits,
    get_active_habits,
    update_habit,
    pause_habit,
    resume_habit,
    quit_habit,
    delete_habit,
    record_completion,
    remove_completion,
    is_completed_on_date,
    get_habits_due_on_date,
    get_habit_progress,
    calculate_streak,
    get_habit_calendar,
    parse_frequency,
)


class TestParseFrequency:
    """Tests for frequency parsing."""

    def test_parse_daily(self):
        """Parse daily frequency."""
        freq_type, target, days = parse_frequency("daily")

        assert freq_type == "daily"
        assert target == 1
        assert days is None

    def test_parse_weekly(self):
        """Parse weekly frequency."""
        freq_type, target, days = parse_frequency("weekly")

        assert freq_type == "weekly"
        assert target == 1

    def test_parse_weekly_with_target(self):
        """Parse weekly with target."""
        freq_type, target, days = parse_frequency("weekly:3")

        assert freq_type == "weekly"
        assert target == 3

    def test_parse_monthly(self):
        """Parse monthly frequency."""
        freq_type, target, days = parse_frequency("monthly")

        assert freq_type == "monthly"
        assert target == 1

    def test_parse_monthly_with_target(self):
        """Parse monthly with target."""
        freq_type, target, days = parse_frequency("monthly:5")

        assert freq_type == "monthly"
        assert target == 5

    def test_parse_specific_days(self):
        """Parse specific days."""
        freq_type, target, days = parse_frequency("days:mon,wed,fri")

        assert freq_type == "specific_days"
        assert target == 3
        assert days == "mon,wed,fri"


class TestCreateHabit:
    """Tests for habit creation."""

    def test_create_daily_habit(self, db_connection):
        """Create a daily habit."""
        habit = create_habit("Exercise", "daily", conn=db_connection)

        assert habit.id is not None
        assert habit.name == "Exercise"
        assert habit.frequency_type == "daily"
        assert habit.frequency_target == 1
        assert habit.status == "active"

    def test_create_weekly_habit(self, db_connection):
        """Create a weekly habit."""
        habit = create_habit("Review", "weekly:2", conn=db_connection)

        assert habit.frequency_type == "weekly"
        assert habit.frequency_target == 2

    def test_create_with_category(self, db_connection):
        """Create habit with category."""
        habit = create_habit("Meditate", "daily", category="Health", conn=db_connection)

        assert habit.category == "Health"

    def test_create_duplicate_name(self, db_connection):
        """Creating duplicate name should fail."""
        create_habit("Unique Habit", conn=db_connection)

        with pytest.raises(Exception):
            create_habit("Unique Habit", conn=db_connection)


class TestGetHabit:
    """Tests for retrieving habits."""

    def test_get_by_id(self, sample_habits):
        """Get habit by ID."""
        habit = get_habit(sample_habits[0].id)

        assert habit is not None
        assert habit.name == "Exercise"

    def test_get_by_name(self, sample_habits):
        """Get habit by name."""
        habit = get_habit_by_name("Exercise")

        assert habit is not None
        assert habit.id == sample_habits[0].id

    def test_get_by_name_case_insensitive(self, sample_habits):
        """Get habit by name is case insensitive."""
        habit = get_habit_by_name("EXERCISE")

        assert habit is not None


class TestGetAllHabits:
    """Tests for listing habits."""

    def test_get_all(self, sample_habits):
        """Get all habits."""
        habits = get_all_habits()

        assert len(habits) == 3

    def test_filter_by_status(self, sample_habits):
        """Filter habits by status."""
        pause_habit(sample_habits[0].id)

        active = get_all_habits(status="active")
        paused = get_all_habits(status="paused")

        assert len(active) == 2
        assert len(paused) == 1


class TestUpdateHabit:
    """Tests for updating habits."""

    def test_update_name(self, sample_habits):
        """Update habit name."""
        habit = update_habit(sample_habits[0].id, name="Workout")

        assert habit.name == "Workout"

    def test_update_frequency(self, sample_habits):
        """Update habit frequency."""
        habit = update_habit(sample_habits[0].id, frequency="weekly:3")

        assert habit.frequency_type == "weekly"
        assert habit.frequency_target == 3


class TestHabitLifecycle:
    """Tests for habit status changes."""

    def test_pause_habit(self, sample_habits):
        """Pause a habit."""
        habit = pause_habit(sample_habits[0].id)

        assert habit.status == "paused"

    def test_resume_habit(self, sample_habits):
        """Resume a paused habit."""
        pause_habit(sample_habits[0].id)
        habit = resume_habit(sample_habits[0].id)

        assert habit.status == "active"

    def test_quit_habit(self, sample_habits):
        """Quit a habit."""
        habit = quit_habit(sample_habits[0].id)

        assert habit.status == "quit"


class TestDeleteHabit:
    """Tests for deleting habits."""

    def test_delete_habit(self, sample_habits):
        """Delete a habit."""
        habit_id = sample_habits[0].id
        result = delete_habit(habit_id)

        assert result is True
        assert get_habit(habit_id) is None


class TestRecordCompletion:
    """Tests for recording completions."""

    def test_record_completion(self, sample_habits):
        """Record a completion."""
        habit = sample_habits[0]
        today = date.today().isoformat()

        completion = record_completion(habit.id, today)

        assert completion is not None
        assert completion.habit_id == habit.id
        assert completion.completion_date == today

    def test_is_completed_on_date(self, sample_habits):
        """Check if habit is completed on a date."""
        habit = sample_habits[0]
        today = date.today().isoformat()

        assert is_completed_on_date(habit.id, today) is False

        record_completion(habit.id, today)

        assert is_completed_on_date(habit.id, today) is True

    def test_remove_completion(self, sample_habits):
        """Remove a completion."""
        habit = sample_habits[0]
        today = date.today().isoformat()

        record_completion(habit.id, today)
        result = remove_completion(habit.id, today)

        assert result is True
        assert is_completed_on_date(habit.id, today) is False


class TestGetHabitsDueOnDate:
    """Tests for getting habits due on a date."""

    def test_daily_habit_always_due(self, sample_habits):
        """Daily habits are always due."""
        today = date.today()
        habits = get_habits_due_on_date(today)

        # Exercise is daily, should be due
        habit_names = [h.name for h in habits]
        assert "Exercise" in habit_names

    def test_paused_habit_not_due(self, sample_habits):
        """Paused habits are not due."""
        pause_habit(sample_habits[0].id)  # Pause Exercise

        today = date.today()
        habits = get_habits_due_on_date(today)

        habit_names = [h.name for h in habits]
        assert "Exercise" not in habit_names


class TestHabitProgress:
    """Tests for habit progress calculation."""

    def test_daily_progress(self, sample_habits):
        """Progress for daily habit."""
        habit = sample_habits[0]  # Exercise, daily
        today = date.today()

        progress = get_habit_progress(habit, today)

        assert progress["completed"] == 0
        assert progress["target"] == 1
        assert progress["percentage"] == 0
        assert progress["period"] == "day"

    def test_daily_progress_after_completion(self, sample_habits):
        """Progress after completing daily habit."""
        habit = sample_habits[0]
        today = date.today()

        record_completion(habit.id, today.isoformat())
        progress = get_habit_progress(habit, today)

        assert progress["completed"] == 1
        assert progress["percentage"] == 100


class TestCalculateStreak:
    """Tests for streak calculation."""

    def test_no_streak(self, sample_habits):
        """No completions means no streak."""
        habit = sample_habits[0]
        today = date.today()

        streak = calculate_streak(habit, today)

        assert streak == 0

    def test_streak_consecutive_days(self, sample_habits):
        """Streak with consecutive daily completions."""
        habit = sample_habits[0]  # Exercise, daily
        today = date.today()

        # Complete for 3 consecutive days
        for i in range(3):
            day = today - timedelta(days=i)
            record_completion(habit.id, day.isoformat())

        streak = calculate_streak(habit, today)

        assert streak == 3

    def test_streak_broken(self, sample_habits):
        """Streak broken by missed day."""
        habit = sample_habits[0]
        today = date.today()

        # Complete today and 2 days ago (skip yesterday)
        record_completion(habit.id, today.isoformat())
        record_completion(habit.id, (today - timedelta(days=2)).isoformat())

        streak = calculate_streak(habit, today)

        assert streak == 1  # Only today counts


class TestHabitCalendar:
    """Tests for habit calendar."""

    def test_calendar_empty(self, sample_habits):
        """Calendar with no completions."""
        habit = sample_habits[0]
        today = date.today()

        cal = get_habit_calendar(habit.id, today.year, today.month)

        # All days should be False
        assert all(not v for v in cal.values())

    def test_calendar_with_completions(self, sample_habits):
        """Calendar with some completions."""
        habit = sample_habits[0]
        today = date.today()

        # Complete on days 1, 5, 10
        for day in [1, 5, 10]:
            date_str = f"{today.year}-{today.month:02d}-{day:02d}"
            record_completion(habit.id, date_str)

        cal = get_habit_calendar(habit.id, today.year, today.month)

        assert cal[1] is True
        assert cal[5] is True
        assert cal[10] is True
        assert cal[2] is False
