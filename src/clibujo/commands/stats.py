"""Statistics commands for CLIBuJo"""

from datetime import date
from typing import Optional

from rich.console import Console
from rich.table import Table

from ..core.config import Config
from ..core.database import Database
from ..utils.dates import get_month_name

console = Console()


def show_stats(
    config: Config,
    db: Database,
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """Show task statistics"""
    # Default to current year if not specified
    if year is None:
        year = date.today().year

    stats = db.get_stats(year, month)

    console.print()

    # Title
    if month:
        console.print(f"[bold]CLIBuJo Stats: {get_month_name(month)} {year}[/bold]")
    else:
        console.print(f"[bold]CLIBuJo Stats: {year}[/bold]")

    console.print()

    # Overall stats
    overall = stats["overall"]
    total = overall.get("total", 0) or 0

    if total == 0:
        console.print("[dim]No tasks found for this period[/dim]")
        return

    completed = overall.get("completed", 0) or 0
    migrated = overall.get("migrated", 0) or 0
    cancelled = overall.get("cancelled", 0) or 0
    open_tasks = overall.get("open", 0) or 0

    console.print("[bold]Tasks Overview[/bold]")
    console.print("─" * 38)

    pct_complete = (100 * completed / total) if total > 0 else 0
    pct_migrated = (100 * migrated / total) if total > 0 else 0
    pct_cancelled = (100 * cancelled / total) if total > 0 else 0
    pct_open = (100 * open_tasks / total) if total > 0 else 0

    console.print(f"Total tasks:     {total:>4}")
    console.print(f"Completed:       {completed:>4} ({pct_complete:.1f}%)")
    console.print(f"Migrated:        {migrated:>4} ({pct_migrated:.1f}%)")
    console.print(f"Cancelled:       {cancelled:>4} ({pct_cancelled:.1f}%)")
    console.print(f"Still open:      {open_tasks:>4} ({pct_open:.1f}%)")

    console.print()

    # Monthly breakdown (only if not filtering by specific month)
    if not month and stats["monthly"]:
        console.print("[bold]Monthly Breakdown[/bold]")
        console.print("─" * 38)
        console.print("         Tasks  Done  Rate")

        today = date.today()

        for m in stats["monthly"]:
            month_str = m.get("month", "")
            if not month_str:
                continue

            try:
                m_year, m_month = int(month_str[:4]), int(month_str[5:7])
            except (ValueError, IndexError):
                continue

            m_total = m.get("total", 0) or 0
            m_completed = m.get("completed", 0) or 0
            m_rate = int(100 * m_completed / m_total) if m_total > 0 else 0

            month_label = f"{get_month_name(m_month)[:3]} {str(m_year)[2:]}"

            # Mark current month
            suffix = ""
            if m_year == today.year and m_month == today.month:
                suffix = "  (in progress)"

            console.print(f"{month_label:>8}  {m_total:>5}  {m_completed:>4}  {m_rate:>3}%{suffix}")

        console.print()

    # Collection stats
    if stats["collections"]:
        console.print("[bold]Most Active Collections[/bold]")
        console.print("─" * 38)

        for c in stats["collections"][:5]:
            coll_name = c.get("collection", "unknown")
            c_total = c.get("total", 0) or 0
            c_completed = c.get("completed", 0) or 0

            # Shorten long collection names
            if "/" in coll_name:
                coll_name = coll_name.split("/")[-1]
            if len(coll_name) > 15:
                coll_name = coll_name[:12] + "..."

            console.print(f"{coll_name}: {c_total} tasks ({c_completed} complete)")

        console.print()
