"""Index generation for CLIBuJo"""

from datetime import date
from pathlib import Path

from rich.console import Console

from ..core.config import Config
from ..core.database import Database
from ..utils.files import (
    walk_markdown_files,
    get_index_file,
    get_daily_file,
    get_monthly_file,
    get_future_file,
)
from ..utils.dates import get_month_name, format_date

console = Console()


def generate_index(config: Config, db: Database):
    """Generate and display the master index"""
    console.print()
    console.print("[bold]CLIBuJo Index[/bold]")
    console.print()

    today = date.today()

    # Daily logs section
    console.print("[bold cyan]Daily Logs[/bold cyan]")
    daily_dir = config.data_dir / "daily"
    if daily_dir.exists():
        daily_files = sorted(daily_dir.glob("*.md"), reverse=True)[:14]  # Last 2 weeks

        for f in daily_files:
            try:
                date_str = f.stem  # YYYY-MM-DD
                parts = date_str.split("-")
                d = date(int(parts[0]), int(parts[1]), int(parts[2]))

                entries = db.get_entries_by_date(d)
                task_count = sum(1 for e in entries if e.entry_type == "task")
                done_count = sum(1 for e in entries if e.entry_type == "task" and e.status == "complete")

                label = format_date(d, "%b %d")
                if d == today:
                    label = f"[bold]{label} (today)[/bold]"

                if task_count > 0:
                    console.print(f"  {label}: {done_count}/{task_count} tasks")
                else:
                    console.print(f"  {label}: {len(entries)} entries")
            except (ValueError, IndexError):
                continue
    else:
        console.print("  [dim](none)[/dim]")

    console.print()

    # Monthly logs section
    console.print("[bold cyan]Monthly Logs[/bold cyan]")
    months_dir = config.data_dir / "months"
    if months_dir.exists():
        month_files = sorted(months_dir.glob("*.md"), reverse=True)[:6]  # Last 6 months

        for f in month_files:
            try:
                month_str = f.stem  # YYYY-MM
                parts = month_str.split("-")
                year, month = int(parts[0]), int(parts[1])

                entries = db.get_entries_by_month(month_str)
                task_count = sum(1 for e in entries if e.entry_type == "task")
                done_count = sum(1 for e in entries if e.entry_type == "task" and e.status == "complete")

                label = f"{get_month_name(month)} {year}"
                if year == today.year and month == today.month:
                    label = f"[bold]{label} (current)[/bold]"

                if task_count > 0:
                    console.print(f"  {label}: {done_count}/{task_count} tasks")
                else:
                    console.print(f"  {label}")
            except (ValueError, IndexError):
                continue
    else:
        console.print("  [dim](none)[/dim]")

    console.print()

    # Future log
    console.print("[bold cyan]Future Log[/bold cyan]")
    future_file = get_future_file(config.data_dir)
    if future_file.exists():
        # Count entries in future log
        from ..core.parser import parse_file
        entries = parse_file(future_file, config.signifiers)
        task_count = sum(1 for e in entries if e.entry_type.value == "task")
        console.print(f"  {task_count} scheduled items")
    else:
        console.print("  [dim](empty)[/dim]")

    console.print()

    # Collections section
    console.print("[bold cyan]Collections[/bold cyan]")
    collections_dir = config.data_dir / "collections"
    if collections_dir.exists():
        for coll_type_dir in sorted(collections_dir.iterdir()):
            if coll_type_dir.is_dir():
                coll_files = list(coll_type_dir.glob("*.md"))
                if coll_files:
                    console.print(f"  [dim]{coll_type_dir.name}/[/dim]")
                    for f in sorted(coll_files):
                        coll_name = f.stem
                        coll_path = f"{coll_type_dir.name}/{coll_name}"
                        entries = db.get_entries_by_collection(coll_path)
                        task_count = sum(1 for e in entries if e.entry_type == "task")
                        done_count = sum(1 for e in entries if e.entry_type == "task" and e.status == "complete")

                        if task_count > 0:
                            console.print(f"    {coll_name}: {done_count}/{task_count} tasks")
                        elif entries:
                            console.print(f"    {coll_name}: {len(entries)} entries")
                        else:
                            console.print(f"    {coll_name}")
    else:
        console.print("  [dim](none)[/dim]")

    console.print()


def write_index_file(config: Config, db: Database):
    """Write the index to index.md file"""
    index_file = get_index_file(config.data_dir)
    today = date.today()

    lines = [
        f"# CLIBuJo Index",
        f"",
        f"*Generated: {format_date(today)}*",
        f"",
    ]

    # Daily logs
    lines.append("## Daily Logs")
    lines.append("")

    daily_dir = config.data_dir / "daily"
    if daily_dir.exists():
        daily_files = sorted(daily_dir.glob("*.md"), reverse=True)[:30]
        for f in daily_files:
            try:
                date_str = f.stem
                parts = date_str.split("-")
                d = date(int(parts[0]), int(parts[1]), int(parts[2]))
                label = format_date(d, "%B %d, %Y")
                lines.append(f"- [{label}](daily/{f.name})")
            except (ValueError, IndexError):
                continue
    else:
        lines.append("*(none)*")

    lines.append("")

    # Monthly logs
    lines.append("## Monthly Logs")
    lines.append("")

    months_dir = config.data_dir / "months"
    if months_dir.exists():
        month_files = sorted(months_dir.glob("*.md"), reverse=True)
        for f in month_files:
            try:
                month_str = f.stem
                parts = month_str.split("-")
                year, month = int(parts[0]), int(parts[1])
                label = f"{get_month_name(month)} {year}"
                lines.append(f"- [{label}](months/{f.name})")
            except (ValueError, IndexError):
                continue
    else:
        lines.append("*(none)*")

    lines.append("")

    # Future log
    lines.append("## Future Log")
    lines.append("")
    lines.append("- [Future Log](future.md)")
    lines.append("")

    # Collections
    lines.append("## Collections")
    lines.append("")

    collections_dir = config.data_dir / "collections"
    if collections_dir.exists():
        for coll_type_dir in sorted(collections_dir.iterdir()):
            if coll_type_dir.is_dir():
                coll_files = list(coll_type_dir.glob("*.md"))
                if coll_files:
                    lines.append(f"### {coll_type_dir.name.title()}")
                    lines.append("")
                    for f in sorted(coll_files):
                        coll_name = f.stem.replace("-", " ").replace("_", " ").title()
                        lines.append(f"- [{coll_name}](collections/{coll_type_dir.name}/{f.name})")
                    lines.append("")

    # Write file
    index_file.write_text("\n".join(lines), encoding="utf-8")
