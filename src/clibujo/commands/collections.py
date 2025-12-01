"""Collection management commands for CLIBuJo"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..core.config import Config
from ..core.database import Database
from ..utils.files import walk_markdown_files

console = Console()


def list_collections(config: Config, db: Database):
    """List all collections with entry counts"""
    collections_dir = config.data_dir / "collections"

    if not collections_dir.exists():
        console.print("[dim]No collections found[/dim]")
        return

    console.print()
    console.print("[bold]Collections[/bold]")
    console.print()

    # Group by type
    collection_types = {}

    for md_file in walk_markdown_files(collections_dir):
        rel_path = md_file.relative_to(collections_dir)
        parts = rel_path.parts

        if len(parts) >= 2:
            coll_type = parts[0]
            coll_name = md_file.stem
        else:
            coll_type = "other"
            coll_name = md_file.stem

        if coll_type not in collection_types:
            collection_types[coll_type] = []

        # Get entry counts
        coll_path = f"collections/{'/'.join(parts[:-1])}/{md_file.name}" if len(parts) > 1 else f"collections/{md_file.name}"
        entries = db.get_entries_by_file(str(rel_path.parent / md_file.name) if len(parts) > 1 else md_file.name)

        # Try alternate path formats
        if not entries:
            entries = db.get_entries_by_collection(f"{coll_type}/{coll_name}")
        if not entries:
            entries = db.get_entries_by_collection(coll_name)

        task_count = sum(1 for e in entries if e.entry_type == "task")
        done_count = sum(1 for e in entries if e.entry_type == "task" and e.status == "complete")

        collection_types[coll_type].append({
            "name": coll_name,
            "path": str(rel_path),
            "tasks": task_count,
            "done": done_count,
            "total": len(entries),
        })

    # Display
    for coll_type, collections in sorted(collection_types.items()):
        console.print(f"[bold cyan]{coll_type.title()}[/bold cyan]")
        for coll in sorted(collections, key=lambda x: x["name"]):
            if coll["tasks"] > 0:
                pct = int(100 * coll["done"] / coll["tasks"]) if coll["tasks"] > 0 else 0
                console.print(f"  {coll['name']}: {coll['done']}/{coll['tasks']} tasks ({pct}%)")
            else:
                console.print(f"  {coll['name']}: {coll['total']} entries")
        console.print()


def get_collection_entries(config: Config, db: Database, name: str):
    """Get entries for a collection"""
    # Try different path formats
    entries = db.get_entries_by_collection(name)
    if not entries:
        # Try with type prefix
        for coll_type in config.collection_types:
            entries = db.get_entries_by_collection(f"{coll_type}/{name}")
            if entries:
                break

    return entries
