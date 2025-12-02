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
from ..core.mood import (
    get_mood_entries,
    get_medications,
    get_med_logs_for_date,
    get_episodes,
    get_all_baselines,
    get_all_targets,
    MoodEntry,
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

    def add_mood_entry(self, entry: MoodEntry):
        """Add a single mood entry to the PDF."""
        self.set_font("Courier", "", 10)

        # Date header
        try:
            dt = datetime.strptime(entry.date, "%Y-%m-%d")
            day_name = dt.strftime("%a")
            formatted = dt.strftime("%b %d")
            date_str = f"{day_name} {formatted}"
        except ValueError:
            date_str = entry.date

        self.set_font("Helvetica", "B", 10)
        self.cell(30, 6, date_str)

        # Core metrics
        self.set_font("Courier", "", 9)
        metrics = []
        if entry.mood is not None:
            mood_str = f"+{entry.mood}" if entry.mood >= 0 else str(entry.mood)
            metrics.append(f"Mood:{mood_str:>3}")
        if entry.energy is not None:
            metrics.append(f"Energy:{entry.energy:>2}")
        if entry.sleep_hours is not None:
            metrics.append(f"Sleep:{entry.sleep_hours:.1f}h")

        self.cell(0, 6, "  ".join(metrics))
        self.ln()

        # Additional dimensions if present
        extra = []
        if entry.irritability is not None:
            extra.append(f"Irritability:{entry.irritability}")
        if entry.anxiety is not None:
            extra.append(f"Anxiety:{entry.anxiety}")
        if entry.racing_thoughts is not None:
            extra.append(f"Racing:{entry.racing_thoughts}")
        if entry.impulsivity is not None:
            extra.append(f"Impulsivity:{entry.impulsivity}")
        if entry.concentration is not None:
            extra.append(f"Concentration:{entry.concentration}")

        if extra:
            self.set_font("Courier", "", 8)
            self.cell(30, 5, "")
            self.cell(0, 5, "  ".join(extra))
            self.ln()

        # Note if present
        if entry.note:
            self.set_font("Helvetica", "I", 9)
            self.cell(30, 5, "")
            self.multi_cell(0, 5, f'"{entry.note}"')

    def add_mood_chart(self, entries: list, title: str = "Mood Trend"):
        """Add a simple text-based mood chart."""
        if not entries:
            return

        self.subsection_title(title)
        self.set_font("Courier", "", 8)

        # Create a simple ASCII chart
        # Scale: -5 to +5 = 11 levels, we'll use 21 chars width
        chart_width = 21
        mid = chart_width // 2

        for entry in entries:
            if entry.mood is None:
                continue

            try:
                dt = datetime.strptime(entry.date, "%Y-%m-%d")
                date_str = dt.strftime("%m/%d")
            except ValueError:
                date_str = entry.date[:5]

            # Map mood (-5 to +5) to position (0 to 20)
            pos = int((entry.mood + 5) * 2)
            pos = max(0, min(chart_width - 1, pos))

            # Build the bar
            bar = ['.'] * chart_width
            bar[mid] = '|'  # Center line
            bar[pos] = '*'

            self.cell(18, 4, date_str)
            self.cell(0, 4, ''.join(bar) + f"  ({entry.mood:+d})")
            self.ln()

        # Legend
        self.ln(2)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 4, "Scale: -5 (depressed) | 0 (baseline) | +5 (elevated)")
        self.ln(5)

    def add_mood_summary(self, entries: list):
        """Add mood statistics summary."""
        if not entries:
            return

        self.subsection_title("Statistics")
        self.set_font("Courier", "", 10)

        # Calculate stats
        moods = [e.mood for e in entries if e.mood is not None]
        energies = [e.energy for e in entries if e.energy is not None]
        sleeps = [e.sleep_hours for e in entries if e.sleep_hours is not None]

        if moods:
            avg_mood = sum(moods) / len(moods)
            min_mood = min(moods)
            max_mood = max(moods)
            self.cell(0, 6, f"  Mood: avg {avg_mood:+.1f}, range {min_mood:+d} to {max_mood:+d}")
            self.ln()

        if energies:
            avg_energy = sum(energies) / len(energies)
            self.cell(0, 6, f"  Energy: avg {avg_energy:.1f}/10")
            self.ln()

        if sleeps:
            avg_sleep = sum(sleeps) / len(sleeps)
            self.cell(0, 6, f"  Sleep: avg {avg_sleep:.1f} hours")
            self.ln()

        # Count entries
        self.ln(2)
        self.cell(0, 6, f"  Days tracked: {len(entries)}")
        self.ln(5)

    def add_medication_section(self, meds: list, start_date: str, end_date: str):
        """Add medication adherence section."""
        if not meds:
            return

        self.subsection_title("Medications")
        self.set_font("Courier", "", 10)

        for med in meds:
            if not med.active:
                continue
            line = f"  {med.name}"
            if med.dosage:
                line += f" ({med.dosage})"
            if med.time_of_day:
                line += f" - {med.time_of_day}"
            self.cell(0, 6, line)
            self.ln()

        self.ln(3)

    def add_episode_section(self, episodes: list):
        """Add episode history section."""
        if not episodes:
            return

        self.subsection_title("Episodes")
        self.set_font("Courier", "", 10)

        for ep in episodes:
            duration = ""
            if ep.end_date:
                try:
                    start = datetime.strptime(ep.start_date, "%Y-%m-%d")
                    end = datetime.strptime(ep.end_date, "%Y-%m-%d")
                    days = (end - start).days + 1
                    duration = f" ({days} days)"
                except ValueError:
                    pass
                date_range = f"{ep.start_date} to {ep.end_date}"
            else:
                date_range = f"{ep.start_date} - ongoing"

            self.cell(0, 6, f"  {ep.type.title()}: {date_range}{duration}")
            self.ln()

            if ep.severity:
                self.cell(0, 5, f"    Severity: {ep.severity}/5")
                self.ln()
            if ep.note:
                self.set_font("Helvetica", "I", 9)
                self.cell(0, 5, f"    {ep.note}")
                self.ln()
                self.set_font("Courier", "", 10)

        self.ln(3)

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


def export_mood(
    start_date: str,
    end_date: str,
    output_path: Optional[Path] = None,
    include_chart: bool = True,
    include_meds: bool = True,
    include_episodes: bool = True,
) -> Path:
    """Export mood log to PDF for therapy sessions.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_path: Optional output path
        include_chart: Include mood trend chart
        include_meds: Include medication list
        include_episodes: Include episode history

    Returns:
        Path to the generated PDF
    """
    check_fpdf()
    ensure_db()

    if output_path is None:
        output_path = Path(f"mood_report_{start_date}_to_{end_date}.pdf")

    # Get mood entries
    entries = get_mood_entries(start_date, end_date)

    # Calculate date range for title
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        title_range = f"{start_dt.strftime('%b %d')} - {end_dt.strftime('%b %d, %Y')}"
    except ValueError:
        title_range = f"{start_date} to {end_date}"

    pdf = BujoPDF(title=f"Mood Report: {title_range}")
    pdf.add_page()

    # Summary section
    pdf.section_title("Summary")
    pdf.add_mood_summary(entries)

    # Mood trend chart
    if include_chart and entries:
        pdf.add_mood_chart(entries)

    # Daily entries
    pdf.section_title("Daily Log")
    if entries:
        for entry in entries:
            pdf.add_mood_entry(entry)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, "  No mood entries for this period.")
        pdf.ln()

    # Medications
    if include_meds:
        meds = get_medications(active_only=False)
        if meds:
            pdf.add_page()
            pdf.section_title("Medications")
            pdf.add_medication_section(meds, start_date, end_date)

    # Episodes
    if include_episodes:
        episodes = get_episodes(months=12)
        # Filter to relevant date range
        relevant_episodes = []
        for ep in episodes:
            # Include if episode overlaps with our date range
            if ep.end_date:
                if ep.start_date <= end_date and ep.end_date >= start_date:
                    relevant_episodes.append(ep)
            else:
                if ep.start_date <= end_date:
                    relevant_episodes.append(ep)

        if relevant_episodes:
            if not include_meds:
                pdf.add_page()
            pdf.section_title("Episodes")
            pdf.add_episode_section(relevant_episodes)

    # Baselines and targets
    baselines = get_all_baselines()
    targets = get_all_targets()

    if baselines or targets:
        pdf.section_title("Reference Values")

        if targets:
            pdf.subsection_title("Your Targets")
            pdf.set_font("Courier", "", 10)
            for metric, value in targets.items():
                pdf.cell(0, 6, f"  {metric}: {value}")
                pdf.ln()
            pdf.ln(3)

        if baselines:
            pdf.subsection_title("Your Baselines")
            pdf.set_font("Courier", "", 10)
            for bl in baselines:
                if bl.std_dev:
                    low = bl.value - bl.std_dev
                    high = bl.value + bl.std_dev
                    pdf.cell(0, 6, f"  {bl.metric}: {bl.value:.1f} (range {low:.1f} to {high:.1f})")
                else:
                    pdf.cell(0, 6, f"  {bl.metric}: {bl.value:.1f}")
                pdf.ln()

    # Footer note for therapist
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    pdf.ln()
    pdf.cell(0, 5, "CLIBuJo Mood Tracking Report")

    pdf.output(str(output_path))
    return output_path


def export_mood_month(
    year: int,
    month: int,
    output_path: Optional[Path] = None,
) -> Path:
    """Export a month of mood data to PDF.

    Args:
        year: Year
        month: Month (1-12)
        output_path: Optional output path

    Returns:
        Path to the generated PDF
    """
    days_in_month = monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{days_in_month:02d}"

    if output_path is None:
        month_name = date(year, month, 1).strftime("%B_%Y")
        output_path = Path(f"mood_report_{month_name}.pdf")

    return export_mood(start_date, end_date, output_path)
