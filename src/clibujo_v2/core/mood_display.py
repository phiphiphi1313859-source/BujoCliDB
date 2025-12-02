"""Display functions for mood tracking output."""

from datetime import datetime, date, timedelta
from typing import Optional, List
import calendar

from .mood import (
    MoodEntry, get_mood_entry, get_mood_entries, get_recent_mood_entries,
    get_watch_data, get_med_logs_for_date, get_episodes,
    get_all_baselines, get_all_targets,
)
from .mood_analysis import calculate_correlations, check_patterns


def format_mood_bar(value: Optional[int], min_val: int, max_val: int, width: int = 20) -> str:
    """Format a value as a text-based bar."""
    if value is None:
        return "(not logged)"
    range_size = max_val - min_val
    normalized = (value - min_val) / range_size
    filled = int(normalized * width)
    return "#" * filled + "-" * (width - filled)


def compare_baseline(metric: str, value: Optional[float], baselines: dict) -> str:
    """Compare a value against its baseline."""
    if value is None or metric not in baselines:
        return ""
    b = baselines[metric]
    if value > b.value + b.std_dev:
        return " ^ above baseline"
    elif value < b.value - b.std_dev:
        return " v below baseline"
    return ""


def format_mood_today(date_str: str) -> str:
    """Format a single day's mood entry for display."""
    entry = get_mood_entry(date_str)
    watch = get_watch_data(date_str)
    meds = get_med_logs_for_date(date_str)
    baselines = {b.metric: b for b in get_all_baselines()}
    targets = get_all_targets()

    # Parse date for display
    dt = datetime.fromisoformat(date_str)
    day_name = dt.strftime("%A")
    date_display = dt.strftime("%B %d, %Y")

    lines = []
    lines.append(f"\n{date_display} ({day_name})")
    lines.append("=" * 50)

    if not entry:
        lines.append("\n(No mood entry for this date.)\n")
        return "\n".join(lines)

    # Logged dimensions
    lines.append("\nLOGGED")

    if entry.mood is not None:
        sign = "+" if entry.mood > 0 else ""
        bar = format_mood_bar(entry.mood, -5, 5)
        lines.append(f"  Mood:        {sign}{entry.mood:>2}  {bar}{compare_baseline('mood', entry.mood, baselines)}")

    if entry.energy is not None:
        bar = format_mood_bar(entry.energy, 1, 10)
        lines.append(f"  Energy:      {entry.energy:>3}  {bar}{compare_baseline('energy', entry.energy, baselines)}")

    if entry.irritability is not None:
        bar = format_mood_bar(entry.irritability, 0, 5)
        lines.append(f"  Irritability:{entry.irritability:>3}  {bar}")

    if entry.anxiety is not None:
        bar = format_mood_bar(entry.anxiety, 0, 5)
        lines.append(f"  Anxiety:     {entry.anxiety:>3}  {bar}")

    if entry.racing_thoughts is not None:
        lines.append(f"  Racing:      {entry.racing_thoughts:>3}")

    if entry.impulsivity is not None:
        lines.append(f"  Impulsivity: {entry.impulsivity:>3}")

    # Sleep
    lines.append("\nSLEEP")
    if entry.sleep_hours is not None:
        sleep_warning = ""
        sleep_target = targets.get("sleep", 7.0)
        if entry.sleep_hours < sleep_target - 1:
            sleep_warning = " (!) below target"
        elif entry.sleep_hours < 5:
            sleep_warning = " (!!) critically low"
        lines.append(f"  Duration:   {entry.sleep_hours:.1f} hrs{sleep_warning}")

    if entry.sleep_quality is not None:
        lines.append(f"  Quality:    {entry.sleep_quality}/5")

    # Watch data
    if watch and (watch.steps or watch.resting_hr or watch.hrv):
        lines.append("\nWATCH DATA")
        if watch.steps:
            steps_note = ""
            if "steps" in baselines:
                b = baselines["steps"]
                if watch.steps > b.value + b.std_dev:
                    steps_note = " ^ above avg"
                elif watch.steps < b.value - b.std_dev:
                    steps_note = " v below avg"
            lines.append(f"  Steps:      {watch.steps:,}{steps_note}")
        if watch.resting_hr:
            lines.append(f"  RHR:        {watch.resting_hr} bpm")
        if watch.hrv:
            lines.append(f"  HRV:        {watch.hrv} ms")

    # Medications
    if meds:
        lines.append("\nMEDS")
        med_line = "  "
        for med in meds:
            taken = med.get("taken")
            if taken:
                med_line += f"[x] {med['name']}  "
            elif taken is None:
                med_line += f"[ ] {med['name']}  "
            else:
                med_line += f"[-] {med['name']}  "
        lines.append(med_line)

    # Note
    if entry.note:
        lines.append(f"\nNOTE")
        lines.append(f'  "{entry.note}"')

    lines.append("")
    return "\n".join(lines)


def format_mood_week(offset: int = 0) -> str:
    """Format 7-day mood view."""
    today = date.today()
    # Calculate week start (Monday)
    week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)
    week_end = week_start + timedelta(days=6)

    lines = []
    lines.append(f"\nWeek of {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}")
    lines.append("=" * 50)

    # Get entries for the week
    entries = {e.date: e for e in get_mood_entries(week_start.isoformat(), week_end.isoformat())}
    watch_data = {d: get_watch_data(d) for d in entries.keys()}

    days = []
    day_names = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        days.append(d.isoformat())
        day_names.append(d.strftime("%a"))

    def format_cell(entry: Optional[MoodEntry], attr: str, future: bool) -> str:
        if future:
            return "-"
        if entry is None:
            return "."
        val = getattr(entry, attr, None)
        if val is None:
            return "."
        if attr == "mood":
            return f"+{val}" if val > 0 else str(val)
        if attr == "sleep_hours":
            return f"{val:.1f}"
        return str(val)

    def calc_avg(attr: str) -> str:
        vals = [getattr(entries.get(d), attr) for d in days
                if d in entries and getattr(entries.get(d), attr) is not None]
        if not vals:
            return "-"
        avg = sum(vals) / len(vals)
        if attr == "mood":
            return f"+{avg:.1f}" if avg > 0 else f"{avg:.1f}"
        if attr == "sleep_hours":
            return f"{avg:.1f}"
        return f"{avg:.1f}"

    # Header
    header = f"{'':8}" + "".join(f"{d:>6}" for d in day_names) + f"{'Avg':>8}"
    lines.append(header)
    lines.append("-" * len(header))

    # Mood row
    row = f"{'Mood':8}"
    for d in days:
        future = datetime.fromisoformat(d).date() > today
        row += f"{format_cell(entries.get(d), 'mood', future):>6}"
    row += f"{calc_avg('mood'):>8}"
    lines.append(row)

    # Energy row
    row = f"{'Energy':8}"
    for d in days:
        future = datetime.fromisoformat(d).date() > today
        row += f"{format_cell(entries.get(d), 'energy', future):>6}"
    row += f"{calc_avg('energy'):>8}"
    lines.append(row)

    # Sleep row
    row = f"{'Sleep':8}"
    for d in days:
        future = datetime.fromisoformat(d).date() > today
        row += f"{format_cell(entries.get(d), 'sleep_hours', future):>6}"
    row += f"{calc_avg('sleep_hours'):>8}"
    lines.append(row)

    # Irritability row
    row = f"{'Irritab':8}"
    for d in days:
        future = datetime.fromisoformat(d).date() > today
        row += f"{format_cell(entries.get(d), 'irritability', future):>6}"
    row += f"{calc_avg('irritability'):>8}"
    lines.append(row)

    # Steps row
    row = f"{'Steps':8}"
    for d in days:
        future = datetime.fromisoformat(d).date() > today
        if future:
            row += f"{'-':>6}"
        elif d in watch_data and watch_data[d] and watch_data[d].steps:
            steps = watch_data[d].steps
            row += f"{steps // 1000}k".rjust(6) if steps >= 1000 else f"{steps}".rjust(6)
        else:
            row += f"{'.':>6}"

    # Steps avg
    step_vals = [watch_data[d].steps for d in days
                 if d in watch_data and watch_data[d] and watch_data[d].steps]
    avg_steps = f"{sum(step_vals) // len(step_vals) // 1000}k" if step_vals else "-"
    row += f"{avg_steps:>8}"
    lines.append(row)

    lines.append("\n. = not logged   - = future")

    # Patterns summary
    warnings = check_patterns(today.isoformat())
    if warnings:
        lines.append("\nPATTERNS")
        for warning in warnings[:2]:  # Show max 2
            first_line = warning.split('\n')[0]
            lines.append(f"  (!) {first_line}")

    lines.append("")
    return "\n".join(lines)


def format_mood_month(year: int, month: int) -> str:
    """Format monthly mood chart."""
    month_name = calendar.month_name[month]

    lines = []
    lines.append(f"\n{month_name} {year}")
    lines.append("=" * 50)

    # Get all entries for the month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    entries = {e.date: e for e in get_mood_entries(first_day.isoformat(), last_day.isoformat())}
    num_days = last_day.day

    # Monthly averages
    lines.append("\nMonthly averages:")

    mood_vals = [e.mood for e in entries.values() if e.mood is not None]
    energy_vals = [e.energy for e in entries.values() if e.energy is not None]
    sleep_vals = [e.sleep_hours for e in entries.values() if e.sleep_hours is not None]

    if mood_vals:
        avg = sum(mood_vals) / len(mood_vals)
        sign = "+" if avg > 0 else ""
        lines.append(f"  Mood: {sign}{avg:.1f}")

    if energy_vals:
        avg = sum(energy_vals) / len(energy_vals)
        lines.append(f"  Energy: {avg:.1f}")

    if sleep_vals:
        avg = sum(sleep_vals) / len(sleep_vals)
        lines.append(f"  Sleep: {avg:.1f} hrs")

    lines.append(f"\n  Days logged: {len(entries)}/{num_days}")

    lines.append("")
    return "\n".join(lines)


def format_mood_trend(months: int) -> str:
    """Format long-term mood trends."""
    today = date.today()

    lines = []
    lines.append(f"\n{months}-Month Overview")
    lines.append("=" * 50)

    # Get monthly averages
    monthly_data = {}

    for i in range(months):
        month_date = today - timedelta(days=i * 30)
        year, month = month_date.year, month_date.month

        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        entries = get_mood_entries(first_day.isoformat(), last_day.isoformat())

        if entries:
            mood_vals = [e.mood for e in entries if e.mood is not None]
            energy_vals = [e.energy for e in entries if e.energy is not None]
            sleep_vals = [e.sleep_hours for e in entries if e.sleep_hours is not None]

            monthly_data[f"{year}-{month:02d}"] = {
                'mood': sum(mood_vals) / len(mood_vals) if mood_vals else None,
                'energy': sum(energy_vals) / len(energy_vals) if energy_vals else None,
                'sleep': sum(sleep_vals) / len(sleep_vals) if sleep_vals else None,
            }

    # Display table
    if monthly_data:
        sorted_months = sorted(monthly_data.keys())[-6:]  # Last 6 months

        # Header
        header = f"{'':8}" + "".join(f"{datetime.strptime(m, '%Y-%m').strftime('%b'):>8}" for m in sorted_months)
        lines.append(header)
        lines.append("-" * len(header))

        # Mood row
        row = f"{'Mood':8}"
        for m in sorted_months:
            val = monthly_data.get(m, {}).get('mood')
            if val is not None:
                sign = "+" if val > 0 else ""
                row += f"{sign}{val:.1f}".rjust(8)
            else:
                row += f"{'-':>8}"
        lines.append(row)

        # Energy row
        row = f"{'Energy':8}"
        for m in sorted_months:
            val = monthly_data.get(m, {}).get('energy')
            row += f"{val:.1f}".rjust(8) if val is not None else f"{'-':>8}"
        lines.append(row)

        # Sleep row
        row = f"{'Sleep':8}"
        for m in sorted_months:
            val = monthly_data.get(m, {}).get('sleep')
            row += f"{val:.1f}".rjust(8) if val is not None else f"{'-':>8}"
        lines.append(row)

    # Episodes
    episodes = get_episodes(months)
    if episodes:
        lines.append("\nEPISODES")
        for ep in episodes:
            if ep.end_date:
                lines.append(f"  {ep.start_date} to {ep.end_date}: {ep.type.capitalize()}" +
                             (f" (severity {ep.severity})" if ep.severity else ""))
            else:
                lines.append(f"  {ep.start_date}: {ep.type.capitalize()} (ongoing)")

    lines.append("")
    return "\n".join(lines)


def format_correlations(days: int) -> str:
    """Format correlation analysis."""
    lines = []
    lines.append(f"\nCorrelation Analysis (last {days} days)")
    lines.append("=" * 50)

    correlations = calculate_correlations(days)

    if not correlations:
        lines.append("\n(Not enough data for correlation analysis. Need at least 14 days.)\n")
        return "\n".join(lines)

    # Sleep -> Mood
    if 'sleep_mood' in correlations:
        sm = correlations['sleep_mood']
        lines.append("\nSLEEP -> MOOD (next day)")
        if sm['low_sleep_avg_mood'] is not None:
            lines.append(f"  < 5 hrs sleep -> mood avg {sm['low_sleep_avg_mood']:+.1f} next day")
        if sm['mid_sleep_avg_mood'] is not None:
            lines.append(f"  5-7 hrs sleep -> mood avg {sm['mid_sleep_avg_mood']:+.1f} next day")
        if sm['high_sleep_avg_mood'] is not None:
            lines.append(f"  > 7 hrs sleep -> mood avg {sm['high_sleep_avg_mood']:+.1f} next day")

    # Sleep -> Energy
    if 'sleep_energy' in correlations:
        se = correlations['sleep_energy']
        lines.append("\nSLEEP -> ENERGY")
        rate = se['low_sleep_high_energy_rate'] * 100
        if rate > 30:
            lines.append(f"  (!) Warning: Low sleep correlates with high energy {rate:.0f}% of time")
            lines.append("      This can indicate hypomania pattern")
        else:
            lines.append(f"  Low sleep -> high energy: {rate:.0f}% of cases")

    # Steps -> Mood
    if 'steps_mood' in correlations:
        stm = correlations['steps_mood']
        lines.append("\nSTEPS -> MOOD")
        if stm['high_steps_avg_mood'] is not None:
            lines.append(f"  > 8000 steps correlates with mood {stm['high_steps_avg_mood']:+.1f} avg")
        if stm['low_steps_avg_mood'] is not None:
            lines.append(f"  < 3000 steps correlates with mood {stm['low_steps_avg_mood']:+.1f} avg")

    lines.append("")
    return "\n".join(lines)


def format_mood_history(days: int) -> str:
    """Format raw mood entry list."""
    entries = get_recent_mood_entries(days)
    entries = sorted(entries, key=lambda e: e.date, reverse=True)

    lines = []
    lines.append(f"\nLast {days} days")
    lines.append("=" * 50)

    if not entries:
        lines.append("\n(No entries.)\n")
        return "\n".join(lines)

    # Header
    header = f"{'Date':12}{'Mood':>6}{'Energy':>8}{'Sleep':>8}{'Irrit':>6}  Note"
    lines.append(header)
    lines.append("-" * 60)

    for entry in entries:
        dt = datetime.fromisoformat(entry.date)
        date_str = dt.strftime("%b %d")

        mood_str = f"{entry.mood:+d}" if entry.mood is not None else "-"
        energy_str = str(entry.energy) if entry.energy is not None else "-"
        sleep_str = f"{entry.sleep_hours:.1f}" if entry.sleep_hours is not None else "-"
        irrit_str = str(entry.irritability) if entry.irritability is not None else "-"
        note_str = (entry.note[:25] + "...") if entry.note and len(entry.note) > 28 else (entry.note or "")

        lines.append(f"{date_str:12}{mood_str:>6}{energy_str:>8}{sleep_str:>8}{irrit_str:>6}  {note_str}")

    lines.append("")
    return "\n".join(lines)
