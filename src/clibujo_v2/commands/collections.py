"""Collection-related CLI commands for CLIBuJo v2."""

import click

from ..core.db import ensure_db
from ..core.collections import (
    create_collection,
    get_collection,
    get_collection_by_name,
    get_all_collections,
    update_collection,
    archive_collection,
    unarchive_collection,
    delete_collection,
    get_collection_stats,
    search_collections,
)
from ..core.entries import get_entries_by_collection
from .display import format_collection


@click.group()
def collections():
    """Manage collections (projects, trackers, lists)."""
    ensure_db()


@collections.command("list")
@click.option("--type", "-t", "coll_type", type=click.Choice(["project", "tracker", "list"]))
@click.option("--archived", "-a", is_flag=True, help="Include archived collections")
def list_collections(coll_type, archived):
    """List all collections."""
    colls = get_all_collections(include_archived=archived, collection_type=coll_type)

    if not colls:
        click.echo("No collections found.")
        return

    # Group by type
    by_type = {}
    for c in colls:
        if c.type not in by_type:
            by_type[c.type] = []
        by_type[c.type].append(c)

    for ctype in ["project", "tracker", "list"]:
        if ctype in by_type:
            click.echo(f"\n{ctype.upper()}S:")
            for c in by_type[ctype]:
                stats = get_collection_stats(c.id)
                archived_mark = " [ARCHIVED]" if c.is_archived else ""

                if ctype == "project":
                    open_count = stats.get("open", 0)
                    complete_count = stats.get("complete", 0)
                    total = open_count + complete_count
                    if total > 0:
                        pct = int((complete_count / total) * 100)
                        click.echo(f"  [{c.id}] {c.name} ({pct}% complete){archived_mark}")
                    else:
                        click.echo(f"  [{c.id}] {c.name}{archived_mark}")
                else:
                    total = stats.get("total", 0)
                    click.echo(f"  [{c.id}] {c.name} ({total} items){archived_mark}")


@collections.command("view")
@click.argument("name_or_id")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show completed tasks too")
def view_collection(name_or_id: str, show_all: bool):
    """View a collection's contents."""
    # Try as ID first
    try:
        coll_id = int(name_or_id)
        coll = get_collection(coll_id)
    except ValueError:
        coll = get_collection_by_name(name_or_id)

    if not coll:
        raise click.ClickException(f"Collection not found: {name_or_id}")

    entries = get_entries_by_collection(coll.id, include_completed=show_all)
    stats = get_collection_stats(coll.id)

    output = format_collection(coll, entries, stats)
    click.echo(output)


@collections.command("create")
@click.argument("name")
@click.option("--type", "-t", "coll_type", type=click.Choice(["project", "tracker", "list"]), default="project")
@click.option("--description", "-d", help="Collection description")
def create_coll(name: str, coll_type: str, description: str):
    """Create a new collection."""
    try:
        coll = create_collection(name, coll_type, description)
        click.echo(f"Created {coll_type}: {coll.name} (id: {coll.id})")
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise click.ClickException(f"Collection already exists: {name}")
        raise


@collections.command("edit")
@click.argument("name_or_id")
@click.option("--name", "-n", "new_name", help="New name")
@click.option("--description", "-d", help="New description")
def edit_coll(name_or_id: str, new_name: str, description: str):
    """Edit a collection."""
    # Find collection
    try:
        coll_id = int(name_or_id)
        coll = get_collection(coll_id)
    except ValueError:
        coll = get_collection_by_name(name_or_id)

    if not coll:
        raise click.ClickException(f"Collection not found: {name_or_id}")

    updated = update_collection(coll.id, name=new_name, description=description)
    if updated:
        click.echo(f"Updated: {updated.name}")
    else:
        click.echo("No changes made.")


@collections.command("archive")
@click.argument("name_or_id")
def archive_coll(name_or_id: str):
    """Archive a collection."""
    try:
        coll_id = int(name_or_id)
        coll = get_collection(coll_id)
    except ValueError:
        coll = get_collection_by_name(name_or_id)

    if not coll:
        raise click.ClickException(f"Collection not found: {name_or_id}")

    updated = archive_collection(coll.id)
    if updated:
        click.echo(f"Archived: {updated.name}")


@collections.command("unarchive")
@click.argument("name_or_id")
def unarchive_coll(name_or_id: str):
    """Unarchive a collection."""
    try:
        coll_id = int(name_or_id)
        coll = get_collection(coll_id)
    except ValueError:
        coll = get_collection_by_name(name_or_id)

    if not coll:
        raise click.ClickException(f"Collection not found: {name_or_id}")

    updated = unarchive_collection(coll.id)
    if updated:
        click.echo(f"Unarchived: {updated.name}")


@collections.command("delete")
@click.argument("name_or_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option("--keep-entries", is_flag=True, help="Keep entries (unlink from collection)")
def delete_coll(name_or_id: str, yes: bool, keep_entries: bool):
    """Delete a collection."""
    try:
        coll_id = int(name_or_id)
        coll = get_collection(coll_id)
    except ValueError:
        coll = get_collection_by_name(name_or_id)

    if not coll:
        raise click.ClickException(f"Collection not found: {name_or_id}")

    stats = get_collection_stats(coll.id)
    entry_count = stats.get("total", 0)

    if not yes:
        if entry_count > 0:
            if keep_entries:
                msg = f"Delete '{coll.name}'? ({entry_count} entries will be unlinked)"
            else:
                msg = f"Delete '{coll.name}' and {entry_count} entries?"
        else:
            msg = f"Delete '{coll.name}'?"
        click.confirm(msg, abort=True)

    if delete_collection(coll.id, delete_entries=not keep_entries):
        click.echo(f"Deleted: {coll.name}")
    else:
        raise click.ClickException("Failed to delete collection")


@collections.command("search")
@click.argument("query")
@click.option("--archived", "-a", is_flag=True, help="Include archived collections")
def search_colls(query: str, archived: bool):
    """Search collections by name."""
    results = search_collections(query, include_archived=archived)

    if not results:
        click.echo("No collections found.")
        return

    click.echo(f"Found {len(results)} collection(s):\n")
    for c in results:
        stats = get_collection_stats(c.id)
        archived_mark = " [ARCHIVED]" if c.is_archived else ""
        click.echo(f"  [{c.id}] {c.name} ({c.type}, {stats.get('total', 0)} items){archived_mark}")
