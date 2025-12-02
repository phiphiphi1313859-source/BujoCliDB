"""Mood tracking CLI commands for CLIBuJo v2."""

import click
from datetime import date, datetime, timedelta
from typing import Optional

from ..core.db import ensure_db
from ..core.mood import (
    MoodEntry, WatchData, Medication, Episode, MoodTrigger,
    get_mood_entry, save_mood_entry, undo_mood_entry,
    get_watch_data, save_watch_data,
    get_medications, get_medication_by_name, add_medication,
    deactivate_medication, log_medication, get_med_logs_for_date,
    get_current_episode, start_episode, end_episode, add_episode, get_episodes,
    get_mood_triggers, add_mood_trigger, set_mood_trigger_active, delete_mood_trigger,
    get_baseline, get_all_baselines, set_target, get_all_targets,
)
from ..core.mood_analysis import check_patterns, calculate_baseline
from ..core.mood_display import (
    format_mood_today, format_mood_week, format_mood_month,
    format_mood_trend, format_correlations, format_mood_history,
)


def parse_mood_date(date_str: Optional[str]) -> str:
    """Parse date string or return today's date."""
    if date_str is None:
        return date.today().isoformat()
    if date_str == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    if date_str == "today":
        return date.today().isoformat()
    # Try to parse as date
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed.date().isoformat()
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


@click.group()
def mood():
    """Mood tracking for mental health management."""
    ensure_db()


# ============ Logging Commands ============

@mood.command("log")
@click.option("--date", "-d", "date_str", default=None, help="Date (YYYY-MM-DD or 'yesterday')")
def mood_log(date_str: Optional[str]):
    """Full daily entry (interactive)."""
    target_date = parse_mood_date(date_str)
    existing = get_mood_entry(target_date)

    click.echo(f"\nLogging for {target_date}\n")

    if existing and existing.mood is not None:
        click.echo("(Existing entry found. Values will be updated.)\n")

    # Prompt for each dimension
    mood_val = click.prompt("Mood (-5 to +5)", type=click.IntRange(-5, 5),
                            default=existing.mood if existing else None, show_default=True)
    energy = click.prompt("Energy (1-10)", type=click.IntRange(1, 10),
                          default=existing.energy if existing else None, show_default=True)
    sleep_hours = click.prompt("Sleep hours", type=float,
                               default=existing.sleep_hours if existing else None, show_default=True)
    sleep_quality = click.prompt("Sleep quality (1-5)", type=click.IntRange(1, 5),
                                 default=existing.sleep_quality if existing else None, show_default=True)
    irritability = click.prompt("Irritability (0-5)", type=click.IntRange(0, 5),
                                default=existing.irritability if existing else 0, show_default=True)
    anxiety = click.prompt("Anxiety (0-5)", type=click.IntRange(0, 5),
                           default=existing.anxiety if existing else 0, show_default=True)
    note = click.prompt("Note (optional)", default=existing.note if existing else "",
                        show_default=False)

    entry = MoodEntry(
        date=target_date,
        mood=mood_val,
        energy=energy,
        sleep_hours=sleep_hours,
        sleep_quality=sleep_quality,
        irritability=irritability,
        anxiety=anxiety,
        note=note if note else None,
    )

    save_mood_entry(entry)
    click.echo(f"\n[x] Logged for {target_date}")

    # Check for patterns
    warnings = check_patterns(target_date)
    for warning in warnings:
        click.echo(f"\n(!) {warning}")


@mood.command("quick")
@click.argument("mood_val", type=click.IntRange(-5, 5))
@click.argument("energy", type=click.IntRange(1, 10))
@click.argument("sleep", type=float)
@click.option("--date", "-d", "date_str", default=None, help="Date (YYYY-MM-DD or 'yesterday')")
def mood_quick(mood_val: int, energy: int, sleep: float, date_str: Optional[str]):
    """Fast minimal entry: mood energy sleep."""
    target_date = parse_mood_date(date_str)

    entry = MoodEntry(
        date=target_date,
        mood=mood_val,
        energy=energy,
        sleep_hours=sleep,
    )
    save_mood_entry(entry)

    sign = "+" if mood_val > 0 else ""
    click.echo(f"[x] Logged for {target_date}: mood {sign}{mood_val}, energy {energy}, sleep {sleep}hrs")

    # Check for patterns
    warnings = check_patterns(target_date)
    for warning in warnings:
        click.echo(f"\n(!) {warning}")


@mood.command("add")
@click.argument("values", nargs=-1)
@click.option("--date", "-d", "date_str", default=None, help="Date (YYYY-MM-DD or 'yesterday')")
def mood_add_dimensions(values: tuple, date_str: Optional[str]):
    """Add dimensions to today's entry. Format: dim:value dim:value"""
    if not values:
        click.echo("Error: No values provided. Use format: racing:3 impulsivity:2")
        return

    target_date = parse_mood_date(date_str)

    # Parse key:value pairs
    dimension_map = {
        "racing": "racing_thoughts",
        "impulsivity": "impulsivity",
        "concentration": "concentration",
        "social": "social_drive",
        "appetite": "appetite",
        "mood": "mood",
        "energy": "energy",
        "sleep": "sleep_hours",
        "sleep_quality": "sleep_quality",
        "irritability": "irritability",
        "anxiety": "anxiety",
    }

    updates = {}
    for item in values:
        if ":" not in item:
            click.echo(f"Error: Invalid format: {item}. Use dim:value")
            return
        key, val = item.split(":", 1)
        key = key.lower()
        if key not in dimension_map:
            click.echo(f"Error: Unknown dimension: {key}")
            return
        try:
            if key == "sleep":
                updates[dimension_map[key]] = float(val)
            else:
                updates[dimension_map[key]] = int(val)
        except ValueError:
            click.echo(f"Error: Invalid value for {key}: {val}")
            return

    entry = MoodEntry(date=target_date, **updates)
    save_mood_entry(entry)

    added = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in updates.items())
    click.echo(f"[x] Added to {target_date}: {added}")


@mood.command("watch")
@click.argument("values", nargs=-1)
@click.option("--date", "-d", "date_str", default=None, help="Date (YYYY-MM-DD)")
def mood_watch(values: tuple, date_str: Optional[str]):
    """Log watch data. Format: steps:8500 rhr:62 hrv:45"""
    if not values:
        click.echo("Error: No values provided. Use format: steps:8500 rhr:62")
        return

    target_date = parse_mood_date(date_str)

    metric_map = {
        "steps": "steps",
        "rhr": "resting_hr",
        "hrv": "hrv",
    }

    updates = {}
    for item in values:
        if ":" not in item:
            click.echo(f"Error: Invalid format: {item}. Use metric:value")
            return
        key, val = item.split(":", 1)
        key = key.lower()
        if key not in metric_map:
            click.echo(f"Error: Unknown metric: {key}. Valid: steps, rhr, hrv")
            return
        try:
            updates[metric_map[key]] = int(val)
        except ValueError:
            click.echo(f"Error: Invalid value for {key}: {val}")
            return

    data = WatchData(date=target_date, **updates)
    save_watch_data(data)

    click.echo(f"[x] Added watch data for {target_date}")


@mood.command("note")
@click.argument("text", required=False)
@click.option("--date", "-d", "date_str", default=None, help="Date (YYYY-MM-DD)")
def mood_note(text: Optional[str], date_str: Optional[str]):
    """Add/update today's note."""
    target_date = parse_mood_date(date_str)

    if text is None:
        text = click.prompt("Note")

    entry = MoodEntry(date=target_date, note=text)
    save_mood_entry(entry)
    click.echo(f"[x] Note saved for {target_date}")


# ============ Viewing Commands ============

@mood.command("today")
def mood_today():
    """Show today's mood entry."""
    output = format_mood_today(date.today().isoformat())
    click.echo(output)


@mood.command("yesterday")
def mood_yesterday():
    """Show yesterday's mood entry."""
    yesterday_date = (date.today() - timedelta(days=1)).isoformat()
    output = format_mood_today(yesterday_date)
    click.echo(output)


@mood.command("week")
@click.option("--offset", "-o", default=0, help="Week offset (0=current, 1=last week, etc)")
def mood_week(offset: int):
    """Show 7-day mood view."""
    output = format_mood_week(offset)
    click.echo(output)


@mood.command("month")
@click.option("--month", "-m", "month_str", default=None, help="Month (YYYY-MM)")
def mood_month(month_str: Optional[str]):
    """Show monthly mood summary."""
    if month_str is None:
        target_date = date.today()
    else:
        try:
            target_date = datetime.strptime(month_str, "%Y-%m").date()
        except ValueError:
            click.echo("Error: Invalid month format. Use YYYY-MM")
            return
    output = format_mood_month(target_date.year, target_date.month)
    click.echo(output)


@mood.command("trend")
@click.option("--months", "-m", default=6, help="Number of months to show")
def mood_trend(months: int):
    """Show long-term mood trends."""
    output = format_mood_trend(months)
    click.echo(output)


@mood.command("history")
@click.option("--days", "-d", default=14, help="Number of days to show")
def mood_history(days: int):
    """Show raw mood entry list."""
    output = format_mood_history(days)
    click.echo(output)


# ============ Medication Commands ============

@mood.group()
def meds():
    """Medication tracking commands."""
    pass


@meds.command("list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show inactive medications too")
def meds_list(show_all: bool):
    """List medications."""
    medications = get_medications(active_only=not show_all)

    if not medications:
        click.echo("No medications configured. Use 'bujo mood meds add' to add one.")
        return

    click.echo("\nMedications\n")
    click.echo(f"{'Name':<20} {'Dose':<12} {'Time':<12} {'Status'}")
    click.echo("-" * 60)

    for med in medications:
        status = "active" if med.active else f"inactive ({med.deactivated_at[:10] if med.deactivated_at else ''})"
        click.echo(f"{med.name:<20} {med.dosage or '-':<12} {med.time_of_day or '-':<12} {status}")


@meds.command("add")
@click.argument("name")
@click.option("--dose", "-d", default=None, help="Dosage (e.g., '300mg')")
@click.option("--time", "-t", "time_of_day",
              type=click.Choice(["morning", "afternoon", "evening", "night"]),
              default=None, help="Time of day")
def meds_add(name: str, dose: Optional[str], time_of_day: Optional[str]):
    """Add a new medication."""
    existing = get_medication_by_name(name)
    if existing:
        click.echo(f"Error: Medication '{name}' already exists.")
        return

    med = Medication(name=name, dosage=dose, time_of_day=time_of_day)
    add_medication(med)
    click.echo(f"[x] Added: {name}" + (f" {dose}" if dose else "") +
               (f" ({time_of_day})" if time_of_day else ""))


@meds.command("remove")
@click.argument("name")
def meds_remove(name: str):
    """Deactivate a medication (history preserved)."""
    if deactivate_medication(name):
        click.echo(f"[x] Deactivated: {name}")
    else:
        click.echo(f"Error: Medication '{name}' not found or already inactive.")


@meds.command("log")
@click.argument("name", required=False)
@click.option("--missed", is_flag=True, help="Log as missed")
@click.option("--note", "-n", default=None, help="Note")
@click.option("--date", "-d", "date_str", default=None, help="Date (YYYY-MM-DD)")
def meds_log(name: Optional[str], missed: bool, note: Optional[str], date_str: Optional[str]):
    """Log medication taken/missed."""
    target_date = parse_mood_date(date_str)

    if name is None:
        # Show today's status
        logs = get_med_logs_for_date(target_date)
        if not logs:
            click.echo("No medications configured.")
            return

        for log_entry in logs:
            taken = log_entry.get("taken")
            symbol = "[x]" if taken else ("[ ]" if taken is None else "[-]")
            med_name = log_entry["name"]
            time = log_entry["time_of_day"] or ""
            click.echo(f"{symbol} {med_name} ({time})")
        return

    # Log specific medication
    med = get_medication_by_name(name)
    if not med:
        click.echo(f"Error: Medication '{name}' not found.")
        return

    time_taken = datetime.now().strftime("%H:%M") if not missed else None
    log_medication(med.id, target_date, taken=not missed, time_taken=time_taken, note=note)

    if missed:
        click.echo(f"[-] Logged: {name} missed" + (f" ({note})" if note else ""))
    else:
        click.echo(f"[x] Logged: {name} taken at {time_taken}")


# ============ Episode Commands ============

@mood.group()
def episode():
    """Episode tracking commands."""
    pass


@episode.command("start")
@click.option("--type", "-t", "ep_type", required=True,
              type=click.Choice(["depression", "hypomania", "mania", "mixed"]),
              help="Episode type")
@click.option("--date", "-d", "date_str", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--severity", "-s", type=click.IntRange(1, 5), default=None, help="Severity (1-5)")
def episode_start(ep_type: str, date_str: Optional[str], severity: Optional[int]):
    """Start tracking an episode."""
    current = get_current_episode()
    if current:
        click.echo(f"(!) Warning: Episode already in progress since {current.start_date} ({current.type})")
        if not click.confirm("End current and start new?"):
            return
        end_episode(current.id)

    start_date_str = parse_mood_date(date_str)
    ep = start_episode(ep_type, start_date_str, severity)
    click.echo(f"[x] Started tracking {ep_type} episode from {start_date_str}")


@episode.command("end")
@click.option("--note", "-n", default=None, help="Note about the episode")
@click.option("--date", "-d", "date_str", default=None, help="End date (YYYY-MM-DD)")
def episode_end_cmd(note: Optional[str], date_str: Optional[str]):
    """End the current episode."""
    current = get_current_episode()
    if not current:
        click.echo("Error: No episode currently in progress.")
        return

    end_date_str = parse_mood_date(date_str)
    ep = end_episode(current.id, end_date_str, note)

    # Calculate duration
    start = datetime.fromisoformat(ep.start_date)
    end = datetime.fromisoformat(ep.end_date)
    days = (end - start).days + 1

    click.echo(f"[x] Ended episode: {ep.start_date} to {ep.end_date} ({days} days)")


@episode.command("add")
@click.option("--start", "-s", "start_date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", "-e", "end_date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--type", "-t", "ep_type", required=True,
              type=click.Choice(["depression", "hypomania", "mania", "mixed"]),
              help="Episode type")
@click.option("--severity", type=click.IntRange(1, 5), default=None, help="Severity (1-5)")
@click.option("--note", "-n", default=None, help="Note")
def episode_add_cmd(start_date: str, end_date: str, ep_type: str,
                    severity: Optional[int], note: Optional[str]):
    """Add a past episode with start and end dates."""
    # Validate dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        click.echo("Error: Invalid date format. Use YYYY-MM-DD")
        return

    if end < start:
        click.echo("Error: End date cannot be before start date.")
        return

    ep = add_episode(start_date, end_date, ep_type, severity, note)
    days = (end - start).days + 1
    click.echo(f"[x] Added past episode: {start_date} to {end_date} ({ep_type}, {days} days)")


@episode.command("list")
@click.option("--months", "-m", default=12, help="Show episodes from last N months")
def episode_list(months: int):
    """List episodes."""
    episodes = get_episodes(months)

    if not episodes:
        click.echo(f"No episodes in the last {months} months.")
        return

    click.echo(f"\nEpisodes (last {months} months)\n")

    for ep in episodes:
        if ep.end_date:
            start = datetime.fromisoformat(ep.start_date)
            end = datetime.fromisoformat(ep.end_date)
            days = (end - start).days + 1
            date_range = f"{ep.start_date} to {ep.end_date} ({days} days)"
        else:
            date_range = f"{ep.start_date} - (ongoing)"

        severity_str = f"Severity: {ep.severity}/5" if ep.severity else ""
        click.echo(f"  {date_range}")
        click.echo(f"    {ep.type.capitalize()} {severity_str}")
        if ep.note:
            click.echo(f'    "{ep.note}"')
        click.echo()


# ============ Trigger Commands ============

@mood.group()
def trigger():
    """Custom trigger commands."""
    pass


@trigger.command("add")
@click.argument("condition")
@click.option("--warn", "-w", "message", required=True, help="Warning message")
def trigger_add(condition: str, message: str):
    """Add a custom trigger. Condition format: 'sleep < 5.5 for 2 days'"""
    if not any(op in condition for op in ["<", ">", "=", "!="]):
        click.echo("Error: Invalid condition. Must contain a comparison operator (<, >, <=, >=, =, !=)")
        return

    trig = add_mood_trigger(condition, message)
    click.echo(f"[x] Added trigger #{trig.id}: {condition}")


@trigger.command("list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show disabled triggers too")
def trigger_list(show_all: bool):
    """List triggers."""
    triggers = get_mood_triggers(active_only=not show_all)

    if not triggers:
        click.echo("No triggers configured.")
        return

    click.echo("\nTriggers\n")
    click.echo(f"{'ID':<5} {'Active':<8} {'Condition':<30} Message")
    click.echo("-" * 70)

    for trig in triggers:
        active = "yes" if trig.active else "no"
        cond = trig.condition if len(trig.condition) < 28 else trig.condition[:25] + "..."
        click.echo(f"{trig.id:<5} {active:<8} {cond:<30} {trig.message}")


@trigger.command("enable")
@click.argument("trigger_id", type=int)
def trigger_enable(trigger_id: int):
    """Enable a trigger."""
    if set_mood_trigger_active(trigger_id, True):
        click.echo(f"[x] Enabled trigger #{trigger_id}")
    else:
        click.echo(f"Error: Trigger #{trigger_id} not found.")


@trigger.command("disable")
@click.argument("trigger_id", type=int)
def trigger_disable(trigger_id: int):
    """Disable a trigger."""
    if set_mood_trigger_active(trigger_id, False):
        click.echo(f"[x] Disabled trigger #{trigger_id}")
    else:
        click.echo(f"Error: Trigger #{trigger_id} not found.")


@trigger.command("delete")
@click.argument("trigger_id", type=int)
def trigger_delete(trigger_id: int):
    """Delete a trigger."""
    if delete_mood_trigger(trigger_id):
        click.echo(f"[x] Deleted trigger #{trigger_id}")
    else:
        click.echo(f"Error: Trigger #{trigger_id} not found.")


# ============ Analysis Commands ============

@mood.command("correlate")
@click.option("--days", "-d", default=90, help="Days of data to analyze")
def mood_correlate(days: int):
    """Show correlation analysis."""
    output = format_correlations(days)
    click.echo(output)


@mood.group()
def baseline():
    """Baseline commands."""
    pass


@baseline.command("show")
def baseline_show():
    """Show current baselines."""
    baselines = get_all_baselines()

    if not baselines:
        click.echo("No baselines calculated yet. Use 'bujo mood baseline recalculate' after logging data.")
        return

    click.echo("\nYour Baselines\n")

    for b in baselines:
        low = b.value - b.std_dev
        high = b.value + b.std_dev
        click.echo(f"  {b.metric:12} {b.value:>6.1f} (std = {b.std_dev:.1f})")
        click.echo(f"  {'':12} Normal range: {low:.1f} to {high:.1f}")
        click.echo()

    click.echo(f"(Based on {baselines[0].days_used} days of data, calculated {baselines[0].calculated_at[:10]})")


@baseline.command("recalculate")
@click.option("--days", "-d", default=90, help="Days of data to use")
def baseline_recalculate(days: int):
    """Recalculate baselines from data."""
    new_baselines = calculate_baseline(days)

    if not new_baselines:
        click.echo("Not enough data. Need at least 14 days of entries.")
        return

    click.echo(f"[x] Recalculated baselines from last {days} days")
    for b in new_baselines:
        click.echo(f"  {b.metric}: {b.value:.1f} (std = {b.std_dev:.1f})")


@mood.command("patterns")
def mood_patterns():
    """Show current detected patterns."""
    warnings = check_patterns(date.today().isoformat())

    if not warnings:
        click.echo("No concerning patterns detected.")
        return

    click.echo("\nDetected Patterns\n")
    for warning in warnings:
        click.echo(f"(!) {warning}\n")


# ============ Target Commands ============

@mood.group(invoke_without_command=True)
@click.pass_context
def target(ctx):
    """View/set targets."""
    if ctx.invoked_subcommand is None:
        # Show current targets
        targets = get_all_targets()
        if not targets:
            click.echo("No targets set. Use 'bujo mood target set <metric> <value>'")
            return

        click.echo("\nCurrent Targets\n")
        for metric, value in targets.items():
            click.echo(f"  {metric}: {value}")


@target.command("view")
def target_view_cmd():
    """View current targets."""
    targets = get_all_targets()
    if not targets:
        click.echo("No targets set. Use 'bujo mood target set <metric> <value>'")
        return

    click.echo("\nCurrent Targets\n")
    for metric, value in targets.items():
        click.echo(f"  {metric}: {value}")


@target.command("set")
@click.argument("metric")
@click.argument("value", type=float)
def target_set_cmd(metric: str, value: float):
    """Set a target for a metric."""
    valid_metrics = ["sleep", "steps", "energy", "mood"]
    if metric.lower() not in valid_metrics:
        click.echo(f"Error: Unknown metric. Valid: {', '.join(valid_metrics)}")
        return

    set_target(metric.lower(), value)
    click.echo(f"[x] {metric.capitalize()} target set: {value}")


# ============ Undo Command ============

@mood.command("undo")
def mood_undo():
    """Revert last change to today's mood entry."""
    today_str = date.today().isoformat()
    restored = undo_mood_entry(today_str)

    if restored:
        click.echo(f"[x] Reverted changes to {today_str}")
    else:
        click.echo(f"No undo history for {today_str}")
