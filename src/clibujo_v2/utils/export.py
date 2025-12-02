"""PDF export functionality for CLIBuJo v2 using fpdf2."""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List
from calendar import monthrange

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

from ..core.db import ensure_db
from ..core.entries import (
    get_entries_by_date,
    get_entries_by_collection,
    get_entries_date_range,
)
from ..core.collections import get_collection, get_collection_by_name, get_all_collections
from ..core.habits import (
    get_all_habits,
    get_habit_progress,
    is_completed_on_date,
    get_habit_calendar,
    get_completions_in_range,
)
from ..core.models import (
    Entry,
    Habit,
    SIGNIFIER_SYMBOLS,
    STATUS_SYMBOLS,
    ENTRY_TYPE_SYMBOLS,
)


class BujoPDF(FPDF):
    """Custom PDF class for bullet journal exports."""

    def __init__(self, title: str = "CLIBuJo Export"):
        super().__init__()
        self.doc_title = title
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Page header."""
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, self.doc_title, border=0, align="C")
        self.ln(15)

    def footer(self):
        """Page footer."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title: str):
        """Add a section title."""
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 10, title, border=0, fill=True)
        self.ln(12)

    def subsection_title(self, title: str):
        """Add a subsection title."""
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, title, border=0)
        self.ln(10)

    def format_entry(self, entry: Entry) -> str:
        """Format an entry for PDF display."""
        parts = []

        # Signifier
        if entry.signifier:
            symbol = SIGNIFIER_SYMBOLS.get(entry.signifier, "")
            if symbol:
                parts.append(symbol)

        # Type/status indicator
        if entry.entry_type == "task":
            symbol = STATUS_SYMBOLS.get(entry.status, "[ ]")
            parts.append(symbol)
        else:
            symbol = ENTRY_TYPE_SYMBOLS.get(entry.entry_type, "-")
            parts.append(symbol)

        # Content
        parts.append(entry.content)

        return " ".join(parts)

    def add_entry(self, entry: Entry):
        """Add an entry line to the PDF."""
        self.set_font("Courier", "", 10)
        text = self.format_entry(entry)
        self.multi_cell(0, 6, f"  {text}")

    def add_entries_section(self, entries: List[Entry], title: str):
        """Add a section with entries."""
        if not entries:
            return

        self.subsection_title(title)
        for entry in entries:
            self.add_entry(entry)
        self.ln(5)

    def add_daily_log(self, entry_date: str, entries: List[Entry]):
        """Add a daily log section."""
        try:
            dt = datetime.strptime(entry_date, "%Y-%m-%d")
            day_name = dt.strftime("%A")
            formatted = dt.strftime("%B %d, %Y")
            title = f"{day_name}, {formatted}"
        except ValueError:
            title = entry_date

        self.section_title(title)

        # Group by type
        events = [e for e in entries if e.entry_type == "event"]
        tasks = [e for e in entries if e.entry_type == "task"]
        notes = [e for e in entries if e.entry_type == "note"]

        if events:
            self.add_entries_section(events, "Events")
        if tasks:
            self.add_entries_section(tasks, "Tasks")
        if notes:
            self.add_entries_section(notes, "Notes")

        if not entries:
            self.set_font("Helvetica", "I", 10)
            self.cell(0, 8, "  (no entries)")
            self.ln()

    def add_habit_section(self, habits: List[Habit], target_date: date):
        """Add habits section."""
        self.section_title("Habits")

        if not habits:
            self.set_font("Helvetica", "I", 10)
            self.cell(0, 8, "  (no habits)")
            self.ln()
            return

        date_str = target_date.isoformat()

        for habit in habits:
            completed = is_completed_on_date(habit.id, date_str)
            progress = get_habit_progress(habit, target_date)

            status = "[x]" if completed else "[ ]"
            freq = habit.get_frequency_display()

            self.set_font("Courier", "", 10)
            line = f"  {status} {habit.name} ({freq})"

            if progress["streak"] > 0:
                line += f" - streak: {progress['streak']}"

            self.cell(0, 6, line)
            self.ln()

        self.ln(5)

    def add_habit_calendar(self, habit: Habit, year: int, month: int):
        """Add a habit calendar for a month."""
        month_name = date(year, month, 1).strftime("%B %Y")
        self.subsection_title(f"{habit.name}: {month_name}")

        cal = get_habit_calendar(habit.id, year, month)
        days_in_month = monthrange(year, month)[1]

        # Header
        self.set_font("Courier", "B", 9)
        self.cell(0, 5, " Mo Tu We Th Fr Sa Su")
        self.ln()

        self.set_font("Courier", "", 9)

        # Find what day the month starts on
        first_day = date(year, month, 1).weekday()

        # Build calendar rows
        row = " " + "   " * first_day

        for day in range(1, days_in_month + 1):
            completed = cal.get(day, False)
            mark = " X" if completed else " ."
            row += f"{mark:>3}"

            day_of_week = (first_day + day - 1) % 7
            if day_of_week == 6:
                self.cell(0, 5, row)
                self.ln()
                row = " "

        if row.strip():
            self.cell(0, 5, row)
            self.ln()

        # Summary
        completed_count = sum(1 for v in cal.values() if v)
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 5, f"  Completed: {completed_count}/{days_in_month} days")
        self.ln(8)


def check_fpdf():
    """Check if fpdf2 is available."""
    if FPDF is None:
        raise ImportError(
            "fpdf2 is required for PDF export. Install with: pip install fpdf2"
        )


def export_today(output_path: Optional[Path] = None) -> Path:
    """Export today's log to PDF."""
    check_fpdf()
    ensure_db()

    today = date.today()
    today_str = today.isoformat()

    if output_path is None:
        output_path = Path(f"bujo_{today_str}.pdf")

    entries = get_entries_by_date(today_str)
    habits = get_all_habits(status="active")

    pdf = BujoPDF(title=f"CLIBuJo - {today_str}")
    pdf.add_page()
    pdf.add_daily_log(today_str, entries)
    pdf.add_habit_section(habits, today)

    pdf.output(str(output_path))
    return output_path


def export_date(target_date: str, output_path: Optional[Path] = None) -> Path:
    """Export a specific date to PDF."""
    check_fpdf()
    ensure_db()

    if output_path is None:
        output_path = Path(f"bujo_{target_date}.pdf")

    entries = get_entries_by_date(target_date)
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    habits = get_all_habits(status="active")

    pdf = BujoPDF(title=f"CLIBuJo - {target_date}")
    pdf.add_page()
    pdf.add_daily_log(target_date, entries)
    pdf.add_habit_section(habits, target)

    pdf.output(str(output_path))
    return output_path


def export_week(
    week_offset: int = 0,
    output_path: Optional[Path] = None,
) -> Path:
    """Export a week to PDF."""
    check_fpdf()
    ensure_db()

    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)

    if output_path is None:
        output_path = Path(f"bujo_week_{monday.isoformat()}.pdf")

    pdf = BujoPDF(title=f"CLIBuJo - Week of {monday.isoformat()}")
    pdf.add_page()

    for i in range(7):
        day = monday + timedelta(days=i)
        day_str = day.isoformat()
        entries = get_entries_by_date(day_str)
        pdf.add_daily_log(day_str, entries)

    # Add habits summary for the week
    habits = get_all_habits(status="active")
    if habits:
        pdf.section_title("Habit Summary (Week)")
        for habit in habits:
            completions = get_completions_in_range(
                habit.id, monday.isoformat(), sunday.isoformat()
            )
            pdf.set_font("Courier", "", 10)
            pdf.cell(0, 6, f"  {habit.name}: {len(completions)} completions")
            pdf.ln()

    pdf.output(str(output_path))
    return output_path


def export_month(
    year: int,
    month: int,
    output_path: Optional[Path] = None,
) -> Path:
    """Export a month to PDF."""
    check_fpdf()
    ensure_db()

    month_name = date(year, month, 1).strftime("%B %Y")
    days_in_month = monthrange(year, month)[1]

    if output_path is None:
        output_path = Path(f"bujo_{year}-{month:02d}.pdf")

    pdf = BujoPDF(title=f"CLIBuJo - {month_name}")
    pdf.add_page()

    # Daily logs
    for day in range(1, days_in_month + 1):
        day_str = f"{year}-{month:02d}-{day:02d}"
        entries = get_entries_by_date(day_str)
        if entries:  # Only include days with entries
            pdf.add_daily_log(day_str, entries)

    # Habit calendars
    habits = get_all_habits(status="active")
    if habits:
        pdf.add_page()
        pdf.section_title("Habit Calendars")
        for habit in habits:
            pdf.add_habit_calendar(habit, year, month)

    pdf.output(str(output_path))
    return output_path


def export_collection(
    collection_name_or_id: str,
    output_path: Optional[Path] = None,
) -> Path:
    """Export a collection to PDF."""
    check_fpdf()
    ensure_db()

    # Find collection
    try:
        coll_id = int(collection_name_or_id)
        coll = get_collection(coll_id)
    except ValueError:
        coll = get_collection_by_name(collection_name_or_id)

    if not coll:
        raise ValueError(f"Collection not found: {collection_name_or_id}")

    if output_path is None:
        safe_name = coll.name.replace(" ", "_").lower()
        output_path = Path(f"bujo_collection_{safe_name}.pdf")

    entries = get_entries_by_collection(coll.id)

    pdf = BujoPDF(title=f"CLIBuJo - {coll.type.title()}: {coll.name}")
    pdf.add_page()

    pdf.section_title(f"{coll.type.upper()}: {coll.name}")

    if coll.description:
        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 6, coll.description)
        pdf.ln(5)

    # Group by type
    tasks = [e for e in entries if e.entry_type == "task"]
    events = [e for e in entries if e.entry_type == "event"]
    notes = [e for e in entries if e.entry_type == "note"]

    pdf.add_entries_section(tasks, "Tasks")
    pdf.add_entries_section(events, "Events")
    pdf.add_entries_section(notes, "Notes")

    # Stats
    if coll.type == "project":
        open_count = sum(1 for t in tasks if t.status == "open")
        complete_count = sum(1 for t in tasks if t.status == "complete")
        total = open_count + complete_count
        if total > 0:
            pct = int((complete_count / total) * 100)
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"Progress: {complete_count}/{total} ({pct}%)")

    pdf.output(str(output_path))
    return output_path


def export_habits(
    year: int,
    month: int,
    output_path: Optional[Path] = None,
) -> Path:
    """Export habit report for a month."""
    check_fpdf()
    ensure_db()

    month_name = date(year, month, 1).strftime("%B %Y")

    if output_path is None:
        output_path = Path(f"bujo_habits_{year}-{month:02d}.pdf")

    habits = get_all_habits()

    pdf = BujoPDF(title=f"CLIBuJo Habits - {month_name}")
    pdf.add_page()

    if not habits:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 10, "No habits found.")
        pdf.output(str(output_path))
        return output_path

    # Group by status
    active = [h for h in habits if h.status == "active"]
    paused = [h for h in habits if h.status == "paused"]
    quit_list = [h for h in habits if h.status == "quit"]
    completed = [h for h in habits if h.status == "completed"]

    if active:
        pdf.section_title("Active Habits")
        for habit in active:
            pdf.add_habit_calendar(habit, year, month)

    if paused:
        pdf.section_title("Paused Habits")
        for habit in paused:
            pdf.set_font("Courier", "", 10)
            pdf.cell(0, 6, f"  {habit.name} ({habit.get_frequency_display()})")
            pdf.ln()

    if quit_list:
        pdf.section_title("Quit Habits")
        for habit in quit_list:
            pdf.set_font("Courier", "", 10)
            pdf.cell(0, 6, f"  {habit.name}")
            pdf.ln()

    if completed:
        pdf.section_title("Completed Habits")
        for habit in completed:
            pdf.set_font("Courier", "", 10)
            pdf.cell(0, 6, f"  {habit.name}")
            pdf.ln()

    pdf.output(str(output_path))
    return output_path


def export_date_range(
    start_date: str,
    end_date: str,
    output_path: Optional[Path] = None,
) -> Path:
    """Export a date range to PDF."""
    check_fpdf()
    ensure_db()

    if output_path is None:
        output_path = Path(f"bujo_{start_date}_to_{end_date}.pdf")

    entries = get_entries_date_range(start_date, end_date)

    pdf = BujoPDF(title=f"CLIBuJo - {start_date} to {end_date}")
    pdf.add_page()

    # Group by date
    by_date = {}
    for entry in entries:
        d = entry.entry_date or "undated"
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(entry)

    for entry_date in sorted(by_date.keys()):
        pdf.add_daily_log(entry_date, by_date[entry_date])

    pdf.output(str(output_path))
    return output_path


def export_all(output_path: Optional[Path] = None) -> Path:
    """Export everything to PDF."""
    check_fpdf()
    ensure_db()

    today = date.today()

    if output_path is None:
        output_path = Path(f"bujo_full_export_{today.isoformat()}.pdf")

    pdf = BujoPDF(title="CLIBuJo Full Export")
    pdf.add_page()

    # Get all entries with dates
    from ..core.db import get_connection

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT DISTINCT entry_date FROM entries
            WHERE entry_date IS NOT NULL
            ORDER BY entry_date DESC
            """
        )
        dates = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

    # Add daily logs
    for entry_date in dates:
        entries = get_entries_by_date(entry_date)
        pdf.add_daily_log(entry_date, entries)

    # Add collections
    collections = get_all_collections()
    if collections:
        pdf.add_page()
        pdf.section_title("Collections")
        for coll in collections:
            entries = get_entries_by_collection(coll.id)
            pdf.subsection_title(f"{coll.type.title()}: {coll.name}")
            for entry in entries:
                pdf.add_entry(entry)
            pdf.ln(5)

    # Add habits
    habits = get_all_habits()
    if habits:
        pdf.add_page()
        pdf.section_title("Habits")
        for habit in habits:
            pdf.add_habit_calendar(habit, today.year, today.month)

    pdf.output(str(output_path))
    return output_path
