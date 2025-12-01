"""Tests for date utilities"""

import pytest
from datetime import date, timedelta

from clibujo.utils.dates import (
    parse_date,
    format_date,
    format_short_date,
    get_month_name,
    get_week_dates,
    parse_month,
    get_next_month,
    get_prev_month,
)


class TestParseDates:
    """Tests for date parsing"""

    def test_parse_today(self):
        result = parse_date("today")
        assert result == date.today()

    def test_parse_yesterday(self):
        result = parse_date("yesterday")
        assert result == date.today() - timedelta(days=1)

    def test_parse_tomorrow(self):
        result = parse_date("tomorrow")
        assert result == date.today() + timedelta(days=1)

    def test_parse_relative_positive(self):
        result = parse_date("+3")
        assert result == date.today() + timedelta(days=3)

    def test_parse_relative_negative(self):
        result = parse_date("-2")
        assert result == date.today() - timedelta(days=2)

    def test_parse_iso_format(self):
        result = parse_date("2024-12-03")
        assert result == date(2024, 12, 3)

    def test_parse_invalid(self):
        result = parse_date("not a date")
        assert result is None


class TestFormatDates:
    """Tests for date formatting"""

    def test_format_date(self):
        d = date(2024, 12, 3)
        result = format_date(d, "%B %d, %Y")
        assert result == "December 03, 2024"

    def test_format_short_date(self):
        d = date(2024, 12, 3)
        result = format_short_date(d, "%b %d")
        assert result == "Dec 03"


class TestMonthUtils:
    """Tests for month utilities"""

    def test_get_month_name(self):
        assert get_month_name(1) == "January"
        assert get_month_name(12) == "December"

    def test_parse_month_yyyy_mm(self):
        result = parse_month("2024-12")
        assert result == (2024, 12)

    def test_parse_month_name(self):
        result = parse_month("december")
        assert result is not None
        assert result[1] == 12

    def test_parse_month_number(self):
        result = parse_month("12")
        assert result is not None
        assert result[1] == 12

    def test_get_next_month(self):
        assert get_next_month(2024, 11) == (2024, 12)
        assert get_next_month(2024, 12) == (2025, 1)

    def test_get_prev_month(self):
        assert get_prev_month(2024, 12) == (2024, 11)
        assert get_prev_month(2024, 1) == (2023, 12)


class TestWeekUtils:
    """Tests for week utilities"""

    def test_get_week_dates(self):
        # Monday week start
        d = date(2024, 12, 4)  # Wednesday
        week = get_week_dates(d, week_start=0)

        assert len(week) == 7
        assert week[0].weekday() == 0  # Monday
        assert d in week
