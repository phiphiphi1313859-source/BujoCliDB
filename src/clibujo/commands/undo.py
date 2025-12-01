"""Undo functionality for CLIBuJo"""

from pathlib import Path

from rich.console import Console

from ..core.config import Config
from ..core.database import Database
from ..core.indexer import Indexer
from ..utils.files import update_line, read_file_lines, write_file_lines, insert_line, delete_line

console = Console()


def do_undo(config: Config, db: Database, indexer: Indexer):
    """Undo the last action"""
    action = db.pop_undo_action()

    if not action:
        console.print("[dim]Nothing to undo[/dim]")
        return

    file_path = Path(action.file_path)

    if action.action_type == "edit":
        # Restore the old line
        if action.old_content is not None:
            update_line(file_path, action.line_number, action.old_content)
            console.print(f"[green]Undone:[/green] Restored line {action.line_number}")
            console.print(f"  {action.old_content[:60]}...")
        else:
            console.print("[red]Cannot undo: no previous content stored[/red]")
            return

    elif action.action_type == "add":
        # Delete the added line
        deleted = delete_line(file_path, action.line_number)
        if deleted:
            console.print(f"[green]Undone:[/green] Removed added line")
            console.print(f"  {deleted[:60]}...")
        else:
            console.print("[red]Cannot undo: line not found[/red]")
            return

    elif action.action_type == "delete":
        # Re-insert the deleted line
        if action.old_content is not None:
            insert_line(file_path, action.line_number, action.old_content)
            console.print(f"[green]Undone:[/green] Restored deleted line")
            console.print(f"  {action.old_content[:60]}...")
        else:
            console.print("[red]Cannot undo: no content stored[/red]")
            return

    else:
        console.print(f"[red]Unknown action type: {action.action_type}[/red]")
        return

    # Reindex the file
    indexer.reindex_file(file_path)

    # Clean up old undo history
    db.clear_old_undo_actions(50)
