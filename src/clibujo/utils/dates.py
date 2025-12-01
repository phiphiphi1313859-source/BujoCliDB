"""Date utilities for CLIBuJo"""

import calendar
from datetime import date, datetime, timedelta
from typing import Optional

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


def parse_date(date_str: str) -> Optional[date]:
    """Parse a date string into a date object"""
    if not date_str:
        return None

    date_str = date_str.strip().lower()

    # Handle relative dates
    today = date.today()

    if date_str in ("today", "now", "t"):
        return today
    if date_str in ("yesterday", "y"):
        return today - timedelta(days=1)
    if date_str in ("tomorrow", "tom"):
        return today + timedelta(days=1)

    # Handle weekday names
    weekdays = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }
    if date_str in weekdays:
        target_weekday = weekdays[date_str]
        days_ahead = target_weekday - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)

    # Handle "last X" or "next X"
    if date_str.startswith("last "):
        weekday_str = date_str[5:]
        if weekday_str in weekdays:
            target_weekday = weekdays[weekday_str]
            days_back = today.weekday() - target_weekday
            if days_back <= 0:
                days_back += 7
            return today - timedelta(days=days_back)

    if date_str.startswith("next "):
        weekday_str = date_str[5:]
        if weekday_str in weekdays:
            target_weekday = weekdays[weekday_str]
            days_ahead = target_weekday - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)

    # Handle relative days: +N, -N
    if date_str.startswith("+") or date_str.startswith("-"):
        try:
            days = int(date_str)
            return today + timedelta(days=days)
        except ValueError:
            pass

    # Try dateutil parser
    try:
        parsed = date_parser.parse(date_str, dayfirst=False)
        return parsed.date()
    except (ValueError, TypeError):
        pass

    return None


def format_date(d: date, fmt: str = "%B %d, %Y") -> str:
    """Format a date"""
    return d.strftime(fmt)


def format_short_date(d: date, fmt: str = "%b %d") -> str:
    """Format a date in short form"""
    return d.strftime(fmt)


def get_month_name(month: int) -> str:
    """Get month name from number"""
    return calendar.month_name[month]


def get_month_abbr(month: int) -> str:
    """Get abbreviated month name"""
    return calendar.month_abbr[month]


def get_week_dates(d: date, week_start: int = 0) -> list[date]:
    """Get all dates in the week containing the given date"""
    # Find the start of the week
    days_since_start = (d.weekday() - week_start) % 7
    week_start_date = d - timedelta(days=days_since_start)

    return [week_start_date + timedelta(days=i) for i in range(7)]


def get_month_calendar(year: int, month: int, week_start: int = 0) -> list[list[Optional[date]]]:
    """Get calendar for a month as list of weeks"""
    cal = calendar.Calendar(firstweekday=week_start)
    weeks = []
    current_week = []

    for day in cal.itermonthdates(year, month):
        current_week.append(day if day.month == month else None)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []

    if current_week:
        weeks.append(current_week)

    return weeks


def get_month_range(year: int, month: int) -> tuple[date, date]:
    """Get first and last date of a month"""
    first = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    last = date(year, month, last_day)
    return first, last


def get_next_month(year: int, month: int) -> tuple[int, int]:
    """Get next month as (year, month) tuple"""
    d = date(year, month, 1) + relativedelta(months=1)
    return d.year, d.month


def get_prev_month(year: int, month: int) -> tuple[int, int]:
    """Get previous month as (year, month) tuple"""
    d = date(year, month, 1) - relativedelta(months=1)
    return d.year, d.month


def parse_month(month_str: str) -> Optional[tuple[int, int]]:
    """Parse a month string into (year, month) tuple"""
    month_str = month_str.strip().lower()

    today = date.today()

    # Handle relative months
    if month_str in ("this", "current", "now"):
        return today.year, today.month
    if month_str in ("next",):
        return get_next_month(today.year, today.month)
    if month_str in ("last", "prev", "previous"):
        return get_prev_month(today.year, today.month)

    # Handle YYYY-MM format
    if "-" in month_str and len(month_str) == 7:
        try:
            parts = month_str.split("-")
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            pass

    # Handle month name (assumes current year)
    month_names = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
    month_abbrs = {name.lower(): i for i, name in enumerate(calendar.month_abbr) if name}

    if month_str in month_names:
        return today.year, month_names[month_str]
    if month_str in month_abbrs:
        return today.year, month_abbrs[month_str]

    # Handle just month number
    try:
        month_num = int(month_str)
        if 1 <= month_num <= 12:
            return today.year, month_num
    except ValueError:
        pass

    return None


def days_between(d1: date, d2: date) -> int:
    """Get number of days between two dates"""
    return abs((d2 - d1).days)


def is_past(d: date) -> bool:
    """Check if date is in the past"""
    return d < date.today()


def is_future(d: date) -> bool:
    """Check if date is in the future"""
    return d > date.today()


def is_today(d: date) -> bool:
    """Check if date is today"""
    return d == date.today()
