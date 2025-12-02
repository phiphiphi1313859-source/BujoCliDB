"""Undo-related CLI commands for CLIBuJo v2."""

import click

from ..core.db import ensure_db
from ..core.undo import (
    undo_last_action,
    undo_multiple,
    get_undo_preview,
    clear_undo_history,
)
from .display import format_undo_preview


@click.group()
def undo():
    """Undo operations."""
    ensure_db()


@undo.command("last")
def last():
    """Undo the last action."""
    result = undo_last_action()

    if result["success"]:
        click.echo(f"Undone: {result['message']}")
    else:
        click.echo(result["message"])


@undo.command("multiple")
@click.argument("count", type=int, default=1)
def multiple(count: int):
    """Undo multiple actions."""
    if count < 1:
        raise click.ClickException("Count must be at least 1")
    if count > 50:
        raise click.ClickException("Maximum 50 undos at once")

    results = undo_multiple(count)

    if not results:
        click.echo("Nothing to undo.")
        return

    click.echo(f"Undone {len(results)} action(s):")
    for r in results:
        click.echo(f"  - {r['message']}")


@undo.command("history")
@click.option("--limit", "-l", default=10, help="Number of actions to show")
def history(limit: int):
    """Show recent undo history."""
    descriptions = get_undo_preview(limit)
    output = format_undo_preview(descriptions)
    click.echo(output)


@undo.command("clear")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def clear(yes: bool):
    """Clear all undo history."""
    if not yes:
        click.confirm("Clear all undo history?", abort=True)

    count = clear_undo_history()
    click.echo(f"Cleared {count} undo entries.")


# Shortcut command for direct undo
@click.command("undo")
def undo_shortcut():
    """Undo the last action (shortcut for 'bujo undo last')."""
    ensure_db()
    result = undo_last_action()

    if result["success"]:
        click.echo(f"Undone: {result['message']}")
    else:
        click.echo(result["message"])
