"""Sync CLI commands for CLIBuJo v2."""

import click

from ..core.db import ensure_db
from ..utils.sync import (
    push,
    pull,
    sync as do_sync,
    get_sync_status,
    list_backups,
    restore_backup,
    create_backup,
    check_rclone,
)


@click.group()
def sync():
    """Sync database with remote storage via rclone."""
    ensure_db()


@sync.command("push")
@click.option("--remote", "-r", help="Remote path (e.g., gdrive:bujo)")
@click.option("--force", "-f", is_flag=True, help="Force push even if remote is newer")
def push_cmd(remote, force):
    """Push local database to remote."""
    success, message = push(remote, force)
    if success:
        click.echo(message)
    else:
        raise click.ClickException(message)


@sync.command("pull")
@click.option("--remote", "-r", help="Remote path (e.g., gdrive:bujo)")
@click.option("--force", "-f", is_flag=True, help="Force pull even if local is newer")
def pull_cmd(remote, force):
    """Pull database from remote."""
    success, message = pull(remote, force)
    if success:
        click.echo(message)
    else:
        raise click.ClickException(message)


@sync.command("auto")
@click.option("--remote", "-r", help="Remote path (e.g., gdrive:bujo)")
def sync_auto(remote):
    """Auto-sync (pull if remote newer, push if local newer)."""
    success, message = do_sync(remote)
    if success:
        click.echo(message)
    else:
        raise click.ClickException(message)


@sync.command("status")
@click.option("--remote", "-r", help="Remote path to check")
def status(remote):
    """Show sync status."""
    info = get_sync_status(remote)

    click.echo("\n== Sync Status ==\n")

    # rclone status
    if info["rclone_available"]:
        click.echo("rclone: installed")
    else:
        click.echo("rclone: NOT INSTALLED")
        click.echo("  Install from: https://rclone.org/install/")

    # Remote config
    if info["remote"]:
        click.echo(f"Remote: {info['remote']}")
    else:
        click.echo("Remote: NOT CONFIGURED")
        click.echo("  Set BUJO_SYNC_REMOTE environment variable")

    click.echo()

    # Timestamps
    if info["local_mtime"]:
        click.echo(f"Local modified:  {info['local_mtime']}")
    else:
        click.echo("Local database:  NOT FOUND")

    if info["remote_mtime"]:
        click.echo(f"Remote modified: {info['remote_mtime']}")
    elif info["remote"]:
        click.echo("Remote database: NOT FOUND")

    # Status
    status_messages = {
        "synced": "In sync",
        "local_newer": "Local is newer (push to sync)",
        "remote_newer": "Remote is newer (pull to sync)",
        "local_only": "Local only (push to upload)",
        "remote_only": "Remote only (pull to download)",
        "none": "No databases found",
        "unknown": "Unknown",
    }

    click.echo(f"\nStatus: {status_messages.get(info['status'], info['status'])}")
    click.echo(f"Backups: {info['backups']} available")


@sync.command("backups")
def list_backups_cmd():
    """List available backups."""
    backups = list_backups()

    if not backups:
        click.echo("No backups found.")
        return

    click.echo("\n== Backups ==\n")
    for b in backups:
        size_kb = b["size"] / 1024
        click.echo(f"  {b['name']}  ({size_kb:.1f} KB)  {b['mtime']}")

    click.echo(f"\nTotal: {len(backups)} backup(s)")


@sync.command("backup")
def backup_cmd():
    """Create a backup of the database."""
    try:
        backup_path = create_backup()
        click.echo(f"Backup created: {backup_path.name}")
    except Exception as e:
        raise click.ClickException(f"Backup failed: {e}")


@sync.command("restore")
@click.argument("backup_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def restore_cmd(backup_name, yes):
    """Restore from a backup."""
    if not yes:
        click.confirm(
            f"Restore from {backup_name}? Current database will be backed up first.",
            abort=True,
        )

    success, message = restore_backup(backup_name)
    if success:
        click.echo(message)
    else:
        raise click.ClickException(message)
