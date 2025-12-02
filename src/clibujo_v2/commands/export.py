"""Export CLI commands for CLIBuJo v2."""

import click
from datetime import date
from pathlib import Path

from ..core.db import ensure_db


@click.group()
def export():
    """Export bullet journal to PDF."""
    ensure_db()


@export.command("today")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_today(output):
    """Export today's log."""
    from ..utils.export import export_today as do_export

    try:
        output_path = Path(output) if output else None
        result = do_export(output_path)
        click.echo(f"Exported to: {result}")
    except ImportError as e:
        raise click.ClickException(str(e))


@export.command("date")
@click.argument("target_date")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_date(target_date, output):
    """Export a specific date's log."""
    from ..utils.export import export_date as do_export

    try:
        output_path = Path(output) if output else None
        result = do_export(target_date, output_path)
        click.echo(f"Exported to: {result}")
    except ImportError as e:
        raise click.ClickException(str(e))


@export.command("week")
@click.option("--offset", "-w", default=0, help="Week offset (0=this week, -1=last week)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_week(offset, output):
    """Export a week's log."""
    from ..utils.export import export_week as do_export

    try:
        output_path = Path(output) if output else None
        result = do_export(offset, output_path)
        click.echo(f"Exported to: {result}")
    except ImportError as e:
        raise click.ClickException(str(e))


@export.command("month")
@click.argument("month_arg", default=None, required=False)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_month(month_arg, output):
    """Export a month's log.

    MONTH_ARG: YYYY-MM format, defaults to current month
    """
    from ..utils.export import export_month as do_export

    if month_arg:
        year, month = map(int, month_arg.split("-"))
    else:
        today = date.today()
        year, month = today.year, today.month

    try:
        output_path = Path(output) if output else None
        result = do_export(year, month, output_path)
        click.echo(f"Exported to: {result}")
    except ImportError as e:
        raise click.ClickException(str(e))


@export.command("collection")
@click.argument("name_or_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_collection(name_or_id, output):
    """Export a collection."""
    from ..utils.export import export_collection as do_export

    try:
        output_path = Path(output) if output else None
        result = do_export(name_or_id, output_path)
        click.echo(f"Exported to: {result}")
    except ImportError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))


@export.command("habits")
@click.argument("month_arg", default=None, required=False)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_habits(month_arg, output):
    """Export habit report for a month.

    MONTH_ARG: YYYY-MM format, defaults to current month
    """
    from ..utils.export import export_habits as do_export

    if month_arg:
        year, month = map(int, month_arg.split("-"))
    else:
        today = date.today()
        year, month = today.year, today.month

    try:
        output_path = Path(output) if output else None
        result = do_export(year, month, output_path)
        click.echo(f"Exported to: {result}")
    except ImportError as e:
        raise click.ClickException(str(e))


@export.command("range")
@click.argument("start_date")
@click.argument("end_date")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_range(start_date, end_date, output):
    """Export a date range."""
    from ..utils.export import export_date_range as do_export

    try:
        output_path = Path(output) if output else None
        result = do_export(start_date, end_date, output_path)
        click.echo(f"Exported to: {result}")
    except ImportError as e:
        raise click.ClickException(str(e))


@export.command("all")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_all(output):
    """Export everything."""
    from ..utils.export import export_all as do_export

    try:
        output_path = Path(output) if output else None
        result = do_export(output_path)
        click.echo(f"Exported to: {result}")
    except ImportError as e:
        raise click.ClickException(str(e))
