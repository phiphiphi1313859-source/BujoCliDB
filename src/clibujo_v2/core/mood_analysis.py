"""Pattern detection and analysis for mood tracking."""

import re
import statistics
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from .mood import (
    MoodEntry, Baseline, MoodTrigger,
    get_mood_entry, get_mood_entries, get_recent_mood_entries,
    get_watch_data, get_all_baselines, save_baseline,
    get_mood_triggers, get_all_targets,
)


def check_patterns(target_date: str) -> List[str]:
    """Check for warning patterns. Returns list of warning messages."""
    warnings = []

    # Get recent entries
    entries = get_recent_mood_entries(14)
    if len(entries) < 3:
        return warnings

    # Sort by date ascending
    entries = sorted(entries, key=lambda e: e.date)

    # Check built-in patterns
    warnings.extend(_check_hypomania_pattern(entries))
    warnings.extend(_check_depression_pattern(entries))
    warnings.extend(_check_mixed_pattern(entries))
    warnings.extend(_check_sleep_pattern(entries))

    # Check custom triggers
    warnings.extend(_check_custom_triggers(entries))

    return warnings


def _check_hypomania_pattern(entries: List[MoodEntry]) -> List[str]:
    """Check for hypomania warning signs."""
    warnings = []

    # Get last 7 days with data
    recent = [e for e in entries[-7:] if e.sleep_hours is not None]

    if len(recent) < 3:
        return warnings

    # Sleep < 6hrs for 3+ consecutive nights
    low_sleep_streak = 0
    for entry in recent:
        if entry.sleep_hours and entry.sleep_hours < 6:
            low_sleep_streak += 1
        else:
            low_sleep_streak = 0

    # High energy
    energy_vals = [e.energy for e in recent if e.energy is not None]
    avg_energy = statistics.mean(energy_vals) if energy_vals else 0

    # Irritability
    irritability_vals = [e.irritability for e in recent if e.irritability is not None]
    avg_irritability = statistics.mean(irritability_vals) if irritability_vals else 0

    if low_sleep_streak >= 3 and avg_energy >= 7:
        msg = "Possible hypomania indicators:\n"
        msg += f"    - Sleep < 6hrs for {low_sleep_streak} consecutive nights\n"
        msg += f"    - Energy elevated (avg {avg_energy:.1f})"
        if avg_irritability >= 2:
            msg += f"\n    - Irritability present (avg {avg_irritability:.1f})"
        warnings.append(msg)

    elif low_sleep_streak >= 2 and avg_energy >= 7 and avg_irritability >= 2:
        warnings.append(
            f"Watch for hypomania pattern:\n"
            f"    - Sleep below 6hrs ({low_sleep_streak} days)\n"
            f"    - Energy elevated (avg {avg_energy:.1f})\n"
            f"    - Irritability present (avg {avg_irritability:.1f})"
        )

    return warnings


def _check_depression_pattern(entries: List[MoodEntry]) -> List[str]:
    """Check for depression warning signs."""
    warnings = []

    recent = [e for e in entries[-7:] if e.mood is not None]

    if len(recent) < 5:
        return warnings

    # Negative mood for 5+ days
    negative_days = sum(1 for e in recent if e.mood is not None and e.mood < 0)
    mood_vals = [e.mood for e in recent if e.mood is not None]
    avg_mood = statistics.mean(mood_vals) if mood_vals else 0

    energy_vals = [e.energy for e in recent if e.energy is not None]
    avg_energy = statistics.mean(energy_vals) if energy_vals else 5

    sleep_vals = [e.sleep_hours for e in recent if e.sleep_hours is not None]
    avg_sleep = statistics.mean(sleep_vals) if sleep_vals else 7

    if negative_days >= 5 and avg_energy < 4:
        msg = "Possible depression indicators:\n"
        msg += f"    - Mood negative for {negative_days}+ days (avg {avg_mood:.1f})\n"
        msg += f"    - Energy low (avg {avg_energy:.1f})"
        if avg_sleep > 8:
            msg += f"\n    - Sleep increased (avg {avg_sleep:.1f} hrs)"
        warnings.append(msg)

    return warnings


def _check_mixed_pattern(entries: List[MoodEntry]) -> List[str]:
    """Check for mixed state warning signs (highest risk)."""
    warnings = []

    recent = [e for e in entries[-3:] if e.mood is not None and e.energy is not None]

    if len(recent) < 2:
        return warnings

    # Low mood + high energy = mixed state danger
    for entry in recent:
        if entry.mood is not None and entry.mood <= -2 and entry.energy is not None and entry.energy >= 7:
            warnings.append(
                f"POSSIBLE MIXED STATE ({entry.date}):\n"
                f"    - Low mood ({entry.mood}) combined with high energy ({entry.energy})\n"
                f"    Mixed states carry higher risk. Consider contacting care team."
            )
            break

    return warnings


def _check_sleep_pattern(entries: List[MoodEntry]) -> List[str]:
    """Check sleep-specific patterns."""
    warnings = []

    recent = [e for e in entries[-5:] if e.sleep_hours is not None]

    if len(recent) < 2:
        return warnings

    targets = get_all_targets()
    sleep_target = targets.get("sleep", 7.0)

    # Critical low sleep
    last_entry = recent[-1] if recent else None
    if last_entry and last_entry.sleep_hours and last_entry.sleep_hours < 5:
        consecutive_low = 0
        for entry in reversed(recent):
            if entry.sleep_hours and entry.sleep_hours < 5.5:
                consecutive_low += 1
            else:
                break

        if consecutive_low >= 2:
            warnings.append(
                f"Sleep critically low:\n"
                f"    - Below 5.5 hrs for {consecutive_low} days\n"
                f"    - Last night: {last_entry.sleep_hours} hrs"
            )

    return warnings


def _check_custom_triggers(entries: List[MoodEntry]) -> List[str]:
    """Evaluate custom triggers."""
    warnings = []
    triggers = get_mood_triggers(active_only=True)

    for trigger in triggers:
        try:
            if _evaluate_trigger(trigger.condition, entries):
                warnings.append(trigger.message)
        except Exception:
            # Skip malformed triggers
            pass

    return warnings


def _evaluate_trigger(condition: str, entries: List[MoodEntry]) -> bool:
    """Evaluate a trigger condition against entries.

    Simple parser for conditions like:
    - "sleep < 5.5"
    - "sleep < 5.5 for 2 days"
    - "energy > 7 and irritability > 3"
    """
    condition = condition.strip().lower()

    # Handle "for N days" suffix
    for_match = re.search(r'\s+for\s+(\d+)\s+days?$', condition)
    required_days = 1
    if for_match:
        required_days = int(for_match.group(1))
        condition = condition[:for_match.start()]

    # Split on 'and' / 'or' (simple left-to-right, no precedence)
    if ' and ' in condition:
        parts = condition.split(' and ')
        return all(_evaluate_simple_condition(p.strip(), entries, required_days) for p in parts)
    elif ' or ' in condition:
        parts = condition.split(' or ')
        return any(_evaluate_simple_condition(p.strip(), entries, required_days) for p in parts)
    else:
        return _evaluate_simple_condition(condition, entries, required_days)


def _evaluate_simple_condition(condition: str, entries: List[MoodEntry], required_days: int) -> bool:
    """Evaluate a simple condition like 'sleep < 5.5'."""
    # Parse: metric operator value
    match = re.match(r'(\w+)\s*(<=|>=|<|>|=|!=)\s*([\d.]+)', condition)
    if not match:
        return False

    metric, op, value_str = match.groups()
    target_value = float(value_str)

    # Map metric names to entry attributes
    metric_map = {
        'mood': 'mood',
        'energy': 'energy',
        'sleep': 'sleep_hours',
        'sleep_quality': 'sleep_quality',
        'irritability': 'irritability',
        'anxiety': 'anxiety',
        'racing': 'racing_thoughts',
        'impulsivity': 'impulsivity',
        'concentration': 'concentration',
        'social': 'social_drive',
        'appetite': 'appetite',
    }

    attr = metric_map.get(metric)
    if not attr:
        return False

    # Check recent entries
    recent = entries[-required_days:] if len(entries) >= required_days else entries

    if len(recent) < required_days:
        return False

    matching_days = 0
    for entry in recent:
        val = getattr(entry, attr, None)
        if val is None:
            continue

        if op == '<' and val < target_value:
            matching_days += 1
        elif op == '>' and val > target_value:
            matching_days += 1
        elif op == '<=' and val <= target_value:
            matching_days += 1
        elif op == '>=' and val >= target_value:
            matching_days += 1
        elif op == '=' and val == target_value:
            matching_days += 1
        elif op == '!=' and val != target_value:
            matching_days += 1

    return matching_days >= required_days


def calculate_baseline(days: int = 90) -> List[Baseline]:
    """Calculate baselines from data."""
    entries = get_recent_mood_entries(days)

    if len(entries) < 14:
        return []

    now = datetime.now().isoformat()
    baselines = []

    metrics = [
        ('mood', 'mood'),
        ('energy', 'energy'),
        ('sleep', 'sleep_hours'),
        ('irritability', 'irritability'),
        ('anxiety', 'anxiety'),
    ]

    for metric_name, attr in metrics:
        values = [getattr(e, attr) for e in entries if getattr(e, attr) is not None]
        if len(values) >= 7:
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0

            baseline = Baseline(
                metric=metric_name,
                value=mean,
                std_dev=stdev,
                calculated_at=now,
                days_used=len(entries),
            )
            save_baseline(baseline)
            baselines.append(baseline)

    # Watch data baselines
    steps_values = []
    for entry in entries:
        watch = get_watch_data(entry.date)
        if watch and watch.steps:
            steps_values.append(watch.steps)

    if len(steps_values) >= 7:
        mean = statistics.mean(steps_values)
        stdev = statistics.stdev(steps_values) if len(steps_values) > 1 else 0
        baseline = Baseline(
            metric='steps',
            value=mean,
            std_dev=stdev,
            calculated_at=now,
            days_used=len(steps_values),
        )
        save_baseline(baseline)
        baselines.append(baseline)

    return baselines


def calculate_correlations(days: int = 90) -> Dict[str, Any]:
    """Calculate correlations between metrics."""
    entries = get_recent_mood_entries(days)
    entries = sorted(entries, key=lambda e: e.date)

    if len(entries) < 14:
        return {}

    correlations = {}

    # Sleep -> Mood (next day)
    sleep_mood_pairs = []
    for i in range(len(entries) - 1):
        if entries[i].sleep_hours is not None and entries[i + 1].mood is not None:
            # Check dates are consecutive
            d1 = datetime.fromisoformat(entries[i].date)
            d2 = datetime.fromisoformat(entries[i + 1].date)
            if (d2 - d1).days == 1:
                sleep_mood_pairs.append((entries[i].sleep_hours, entries[i + 1].mood))

    if len(sleep_mood_pairs) >= 7:
        low_sleep = [m for s, m in sleep_mood_pairs if s < 5]
        mid_sleep = [m for s, m in sleep_mood_pairs if 5 <= s <= 7]
        high_sleep = [m for s, m in sleep_mood_pairs if s > 7]

        correlations['sleep_mood'] = {
            'low_sleep_avg_mood': statistics.mean(low_sleep) if low_sleep else None,
            'mid_sleep_avg_mood': statistics.mean(mid_sleep) if mid_sleep else None,
            'high_sleep_avg_mood': statistics.mean(high_sleep) if high_sleep else None,
        }

    # Sleep -> Energy (same day, inverse in hypomania)
    sleep_energy_pairs = [(e.sleep_hours, e.energy) for e in entries
                          if e.sleep_hours is not None and e.energy is not None]

    if len(sleep_energy_pairs) >= 7:
        low_sleep_high_energy = sum(1 for s, e in sleep_energy_pairs if s < 6 and e >= 7)
        total_low_sleep = sum(1 for s, e in sleep_energy_pairs if s < 6)

        correlations['sleep_energy'] = {
            'low_sleep_high_energy_rate': low_sleep_high_energy / total_low_sleep if total_low_sleep else 0,
            'warning': low_sleep_high_energy >= 3,
        }

    # Steps -> Mood
    steps_mood_pairs = []
    for entry in entries:
        watch = get_watch_data(entry.date)
        if watch and watch.steps and entry.mood is not None:
            steps_mood_pairs.append((watch.steps, entry.mood))

    if len(steps_mood_pairs) >= 7:
        high_steps = [m for s, m in steps_mood_pairs if s > 8000]
        low_steps = [m for s, m in steps_mood_pairs if s < 3000]

        correlations['steps_mood'] = {
            'high_steps_avg_mood': statistics.mean(high_steps) if high_steps else None,
            'low_steps_avg_mood': statistics.mean(low_steps) if low_steps else None,
        }

    return correlations
