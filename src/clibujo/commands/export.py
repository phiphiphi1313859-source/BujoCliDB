"""Export functionality for CLIBuJo"""

from datetime import date
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core.config import Config
from ..core.database import Database
from ..utils.files import read_file_lines, walk_markdown_files
from ..utils.dates import get_month_name, format_date

console = Console()


def do_export(
    config: Config,
    db: Database,
    format: str,
    output: Optional[str],
    year: Optional[int],
    month: Optional[int],
):
    """Export journal to HTML or PDF"""
    format = format.lower()

    if format not in ("html", "pdf"):
        console.print(f"[red]Unsupported format: {format}[/red]")
        console.print("[dim]Supported formats: html, pdf[/dim]")
        return

    # Determine output file
    if output:
        output_path = Path(output)
    else:
        if year and month:
            output_path = Path(f"bujo-{year}-{month:02d}.{format}")
        elif year:
            output_path = Path(f"bujo-{year}.{format}")
        else:
            output_path = Path(f"bujo-export.{format}")

    console.print(f"Exporting to {output_path}...")

    # Generate HTML content
    html_content = _generate_html(config, db, year, month)

    if format == "html":
        output_path.write_text(html_content, encoding="utf-8")
        console.print(f"[green]Exported to {output_path}[/green]")
    elif format == "pdf":
        _export_pdf(html_content, output_path)


def _generate_html(
    config: Config,
    db: Database,
    year: Optional[int],
    month: Optional[int],
) -> str:
    """Generate HTML content for export"""
    today = date.today()

    # Title
    if year and month:
        title = f"Bullet Journal - {get_month_name(month)} {year}"
    elif year:
        title = f"Bullet Journal - {year}"
    else:
        title = "Bullet Journal Export"

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        f"<title>{title}</title>",
        "<meta charset='utf-8'>",
        "<style>",
        _get_css(),
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{title}</h1>",
        f"<p class='generated'>Generated: {format_date(today)}</p>",
    ]

    # Get entries to export
    if month and year:
        # Single month
        month_str = f"{year}-{month:02d}"
        entries = db.get_entries_by_month(month_str)
        _add_entries_html(html_parts, entries, f"{get_month_name(month)} {year}")
    elif year:
        # Full year - by month
        for m in range(1, 13):
            month_str = f"{year}-{m:02d}"
            entries = db.get_entries_by_month(month_str)
            if entries:
                _add_entries_html(html_parts, entries, f"{get_month_name(m)} {year}")
    else:
        # Everything - organize by file
        _add_all_entries_html(config, db, html_parts)

    html_parts.extend([
        "</body>",
        "</html>",
    ])

    return "\n".join(html_parts)


def _add_entries_html(html_parts: list, entries: list, title: str):
    """Add a section of entries to HTML"""
    html_parts.append(f"<h2>{title}</h2>")
    html_parts.append("<ul class='entries'>")

    for entry in entries:
        css_class = f"entry {entry.entry_type}"
        if entry.status:
            css_class += f" {entry.status}"
        if entry.signifier:
            css_class += f" {entry.signifier}"

        marker = ""
        if entry.entry_type == "task":
            status_map = {
                "open": "☐",
                "complete": "☑",
                "migrated": "→",
                "scheduled": "←",
                "cancelled": "⊘",
            }
            marker = status_map.get(entry.status, "☐")
        elif entry.entry_type == "event":
            marker = "○"
        elif entry.entry_type == "note":
            marker = "—"

        sig = ""
        if entry.signifier == "priority":
            sig = "★ "
        elif entry.signifier == "inspiration":
            sig = "! "
        elif entry.signifier == "explore":
            sig = "? "

        html_parts.append(f'<li class="{css_class}">')
        html_parts.append(f'<span class="marker">{marker}</span>')
        html_parts.append(f'<span class="signifier">{sig}</span>')
        html_parts.append(f'<span class="content">{entry.content}</span>')
        html_parts.append("</li>")

    html_parts.append("</ul>")


def _add_all_entries_html(config: Config, db: Database, html_parts: list):
    """Add all entries organized by file"""
    # Daily logs
    daily_dir = config.data_dir / "daily"
    if daily_dir.exists():
        html_parts.append("<h2>Daily Logs</h2>")
        for f in sorted(daily_dir.glob("*.md"), reverse=True):
            rel_path = str(f.relative_to(config.data_dir))
            entries = db.get_entries_by_file(rel_path)
            if entries:
                try:
                    date_str = f.stem
                    parts = date_str.split("-")
                    d = date(int(parts[0]), int(parts[1]), int(parts[2]))
                    title = format_date(d)
                except (ValueError, IndexError):
                    title = f.stem
                _add_entries_html(html_parts, entries, title)

    # Monthly logs
    months_dir = config.data_dir / "months"
    if months_dir.exists():
        html_parts.append("<h2>Monthly Logs</h2>")
        for f in sorted(months_dir.glob("*.md"), reverse=True):
            rel_path = str(f.relative_to(config.data_dir))
            entries = db.get_entries_by_file(rel_path)
            if entries:
                try:
                    month_str = f.stem
                    parts = month_str.split("-")
                    year, month = int(parts[0]), int(parts[1])
                    title = f"{get_month_name(month)} {year}"
                except (ValueError, IndexError):
                    title = f.stem
                _add_entries_html(html_parts, entries, title)

    # Collections
    collections_dir = config.data_dir / "collections"
    if collections_dir.exists():
        html_parts.append("<h2>Collections</h2>")
        for md_file in sorted(walk_markdown_files(collections_dir)):
            rel_path = str(md_file.relative_to(config.data_dir))
            entries = db.get_entries_by_file(rel_path)
            if entries:
                title = md_file.stem.replace("-", " ").replace("_", " ").title()
                _add_entries_html(html_parts, entries, title)


def _get_css() -> str:
    """Return CSS for export"""
    return """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    line-height: 1.6;
    color: #333;
}

h1 {
    border-bottom: 2px solid #333;
    padding-bottom: 0.5rem;
}

h2 {
    margin-top: 2rem;
    color: #555;
}

.generated {
    color: #888;
    font-size: 0.9rem;
}

ul.entries {
    list-style: none;
    padding-left: 0;
}

li.entry {
    padding: 0.3rem 0;
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}

.marker {
    font-family: monospace;
    width: 1.5rem;
    text-align: center;
    flex-shrink: 0;
}

.signifier {
    color: #c00;
    width: 1rem;
    flex-shrink: 0;
}

.content {
    flex-grow: 1;
}

li.complete .content {
    text-decoration: line-through;
    color: #888;
}

li.cancelled .content {
    text-decoration: line-through;
    color: #aaa;
}

li.migrated .content,
li.scheduled .content {
    color: #666;
}

li.priority .content {
    font-weight: 600;
}

@media print {
    body {
        max-width: none;
        padding: 1cm;
    }

    h2 {
        page-break-before: auto;
        page-break-after: avoid;
    }

    li.entry {
        page-break-inside: avoid;
    }
}
"""


def _export_pdf(html_content: str, output_path: Path):
    """Export HTML to PDF using WeasyPrint"""
    try:
        from weasyprint import HTML
    except ImportError:
        console.print("[red]PDF export requires weasyprint[/red]")
        console.print("[dim]Install with: pip install 'clibujo[export]'[/dim]")
        return

    try:
        HTML(string=html_content).write_pdf(output_path)
        console.print(f"[green]Exported to {output_path}[/green]")
    except Exception as e:
        console.print(f"[red]PDF export failed: {e}[/red]")
