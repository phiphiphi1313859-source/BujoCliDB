"""Tests for habit tracking functionality."""

import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from clibujo.core.habits import (
    Frequency,
    FrequencyType,
    Habit,
    HabitStatus,
    HabitStore,
)


class TestFrequency:
    """Tests for Frequency parsing and representation."""

    def test_parse_daily(self):
        freq = Frequency.parse("daily")
        assert freq.type == FrequencyType.DAILY
        assert freq.target == 1

    def test_parse_weekly(self):
        freq = Frequency.parse("weekly")
        assert freq.type == FrequencyType.WEEKLY
        assert freq.target == 1

    def test_parse_weekly_with_target(self):
        freq = Frequency.parse("weekly:3")
        assert freq.type == FrequencyType.WEEKLY
        assert freq.target == 3

    def test_parse_monthly(self):
        freq = Frequency.parse("monthly")
        assert freq.type == FrequencyType.MONTHLY
        assert freq.target == 1

    def test_parse_monthly_with_target(self):
        freq = Frequency.parse("monthly:5")
        assert freq.type == FrequencyType.MONTHLY
        assert freq.target == 5

    def test_parse_specific_days(self):
        freq = Frequency.parse("days:mon,wed,fri")
        assert freq.type == FrequencyType.SPECIFIC_DAYS
        assert freq.days == ["mon", "wed", "fri"]

    def test_str_daily(self):
        freq = Frequency(type=FrequencyType.DAILY)
        assert str(freq) == "daily"

    def test_str_weekly_with_target(self):
        freq = Frequency(type=FrequencyType.WEEKLY, target=3)
        assert str(freq) == "weekly:3"

    def test_str_specific_days(self):
        freq = Frequency(type=FrequencyType.SPECIFIC_DAYS, days=["mon", "fri"])
        assert str(freq) == "days:mon,fri"


class TestHabit:
    """Tests for Habit model."""

    def test_habit_id_generation(self):
        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("daily"),
            created=date.today(),
        )
        assert len(habit.id) == 6
        assert habit.id.isalnum()

    def test_is_due_daily(self):
        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("daily"),
            created=date.today() - timedelta(days=5),
        )
        assert habit.is_due_on(date.today()) is True
        assert habit.is_due_on(date.today() - timedelta(days=1)) is True

    def test_is_due_specific_days(self):
        # Find next Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        next_tuesday = next_monday + timedelta(days=1)

        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("days:mon,wed,fri"),
            created=today - timedelta(days=30),
        )

        assert habit.is_due_on(next_monday) is True
        assert habit.is_due_on(next_tuesday) is False

    def test_is_completed_on(self):
        today = date.today()
        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("daily"),
            created=today - timedelta(days=5),
            completions=[today],
        )
        assert habit.is_completed_on(today) is True
        assert habit.is_completed_on(today - timedelta(days=1)) is False

    def test_daily_streak(self):
        today = date.today()
        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("daily"),
            created=today - timedelta(days=10),
            completions=[
                today,
                today - timedelta(days=1),
                today - timedelta(days=2),
            ],
        )
        assert habit.get_streak(today) == 3

    def test_daily_streak_broken(self):
        today = date.today()
        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("daily"),
            created=today - timedelta(days=10),
            completions=[
                today,
                today - timedelta(days=1),
                # Day 2 missing - streak broken
                today - timedelta(days=3),
            ],
        )
        assert habit.get_streak(today) == 2

    def test_weekly_streak(self):
        today = date.today()
        # Create completions for last 3 weeks
        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("weekly:1"),
            created=today - timedelta(days=30),
            completions=[
                today - timedelta(days=0),   # This week
                today - timedelta(days=7),   # Last week
                today - timedelta(days=14),  # 2 weeks ago
            ],
        )
        streak = habit.get_streak(today)
        assert streak >= 2  # At least 2 complete weeks

    def test_success_rate(self):
        today = date.today()
        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("daily"),
            created=today - timedelta(days=9),  # 10 days including today
            completions=[
                today,
                today - timedelta(days=1),
                today - timedelta(days=2),
                today - timedelta(days=3),
                today - timedelta(days=4),
                # Days 5-9 not completed
            ],
        )
        rate = habit.get_success_rate(10, today)
        assert rate == 50.0  # 5 out of 10 days

    def test_paused_habit_not_due(self):
        habit = Habit(
            name="Exercise",
            frequency=Frequency.parse("daily"),
            created=date.today() - timedelta(days=5),
            status=HabitStatus.PAUSED,
        )
        assert habit.is_due_on(date.today()) is False


class TestHabitStore:
    """Tests for HabitStore file operations."""

    def test_create_and_load_habit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            habit = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today(),
            )
            store.add_habit(habit)

            habits = store.load_all()
            assert len(habits) == 1
            assert habits[0].name == "Exercise"
            assert habits[0].frequency.type == FrequencyType.DAILY

    def test_log_completion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            habit = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today(),
            )
            store.add_habit(habit)

            today = date.today()
            store.log_completion("Exercise", today)

            habits = store.load_all()
            assert today in habits[0].completions

    def test_unlog_completion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            today = date.today()
            habit = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=today,
                completions=[today],
            )
            store.add_habit(habit)

            store.unlog_completion("Exercise", today)

            habits = store.load_all()
            assert today not in habits[0].completions

    def test_change_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            habit = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today(),
            )
            store.add_habit(habit)

            store.change_status("Exercise", HabitStatus.PAUSED)

            habits = store.load_all()
            assert habits[0].status == HabitStatus.PAUSED

    def test_get_due_habits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            # Add daily habit (should be due)
            habit1 = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today() - timedelta(days=1),
            )
            store.add_habit(habit1)

            # Add paused habit (should not be due)
            habit2 = Habit(
                name="Meditate",
                frequency=Frequency.parse("daily"),
                created=date.today() - timedelta(days=1),
                status=HabitStatus.PAUSED,
            )
            store.add_habit(habit2)

            due = store.get_due_habits(date.today())
            assert len(due) == 1
            assert due[0].name == "Exercise"

    def test_duplicate_habit_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            habit = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today(),
            )
            store.add_habit(habit)

            with pytest.raises(ValueError, match="already exists"):
                store.add_habit(habit)

    def test_get_habit_by_partial_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            habit = Habit(
                name="Morning Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today(),
            )
            store.add_habit(habit)

            found = store.get_habit("morning")
            assert found is not None
            assert found.name == "Morning Exercise"

    def test_delete_habit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            habit = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today(),
            )
            store.add_habit(habit)

            store.delete_habit("Exercise")

            habits = store.load_all()
            assert len(habits) == 0

    def test_habit_with_category(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            habit = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today(),
                category="health",
            )
            store.add_habit(habit)

            habits = store.load_all()
            assert habits[0].category == "health"

    def test_habit_with_note(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            habit = Habit(
                name="Exercise",
                frequency=Frequency.parse("daily"),
                created=date.today(),
            )
            store.add_habit(habit)

            today = date.today()
            store.log_completion("Exercise", today, note="30 min run")

            habits = store.load_all()
            assert today in habits[0].notes
            assert habits[0].notes[today] == "30 min run"


class TestHabitMarkdownFormat:
    """Tests for habit markdown file format."""

    def test_markdown_format_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HabitStore(Path(tmpdir))

            today = date.today()

            # Create habits with different statuses and properties
            habits = [
                Habit(
                    name="Exercise",
                    frequency=Frequency.parse("daily"),
                    created=today - timedelta(days=10),
                    completions=[today, today - timedelta(days=1)],
                    category="health",
                ),
                Habit(
                    name="Read",
                    frequency=Frequency.parse("weekly:3"),
                    created=today - timedelta(days=20),
                    status=HabitStatus.PAUSED,
                ),
                Habit(
                    name="Call mom",
                    frequency=Frequency.parse("days:sun"),
                    created=today - timedelta(days=30),
                ),
            ]

            for habit in habits:
                store.add_habit(habit)

            # Reload and verify
            loaded = store.load_all()
            assert len(loaded) == 3

            exercise = next(h for h in loaded if h.name == "Exercise")
            assert exercise.frequency.type == FrequencyType.DAILY
            assert exercise.category == "health"
            assert len(exercise.completions) == 2

            read = next(h for h in loaded if h.name == "Read")
            assert read.frequency.type == FrequencyType.WEEKLY
            assert read.frequency.target == 3
            assert read.status == HabitStatus.PAUSED

            call = next(h for h in loaded if h.name == "Call mom")
            assert call.frequency.type == FrequencyType.SPECIFIC_DAYS
            assert "sun" in call.frequency.days
