"""rclone-based sync for CLIBuJo v2.

Implements last-write-wins sync strategy using rclone.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from ..core.db import get_db_path, get_data_dir


def get_backup_dir() -> Path:
    """Get backup directory."""
    backup_dir = get_data_dir() / "backups"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def get_sync_config() -> dict:
    """Get sync configuration from environment or config."""
    return {
        "remote": os.environ.get("BUJO_SYNC_REMOTE", ""),  # e.g., "gdrive:bujo"
        "enabled": os.environ.get("BUJO_SYNC_ENABLED", "false").lower() == "true",
    }


def check_rclone() -> bool:
    """Check if rclone is available."""
    try:
        result = subprocess.run(
            ["rclone", "version"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def create_backup() -> Path:
    """Create a timestamped backup of the database."""
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError("Database not found")

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"bujo_backup_{timestamp}.db"

    shutil.copy2(db_path, backup_path)

    # Keep only last 10 backups
    backups = sorted(backup_dir.glob("bujo_backup_*.db"), reverse=True)
    for old_backup in backups[10:]:
        old_backup.unlink()

    return backup_path


def get_remote_mtime(remote: str) -> Optional[datetime]:
    """Get modification time of remote database."""
    try:
        result = subprocess.run(
            ["rclone", "lsl", remote],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        # Parse rclone lsl output: "size date time name"
        # Example: "    12345 2025-01-15 10:30:00.000000000 bujo.db"
        parts = result.stdout.strip().split()
        if len(parts) >= 3:
            date_str = f"{parts[1]} {parts[2].split('.')[0]}"
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None


def get_local_mtime() -> Optional[datetime]:
    """Get modification time of local database."""
    db_path = get_db_path()
    if not db_path.exists():
        return None
    return datetime.fromtimestamp(db_path.stat().st_mtime)


def push(remote: Optional[str] = None, force: bool = False) -> Tuple[bool, str]:
    """Push local database to remote.

    Args:
        remote: Remote path (e.g., "gdrive:bujo/bujo.db")
        force: Skip timestamp check

    Returns:
        (success, message) tuple
    """
    if not check_rclone():
        return False, "rclone not installed"

    if not remote:
        config = get_sync_config()
        remote = config.get("remote")
        if not remote:
            return False, "No remote configured. Set BUJO_SYNC_REMOTE environment variable."

    db_path = get_db_path()
    if not db_path.exists():
        return False, "Local database not found"

    # Check timestamps unless forcing
    if not force:
        local_mtime = get_local_mtime()
        remote_mtime = get_remote_mtime(f"{remote}/bujo.db")

        if remote_mtime and local_mtime and remote_mtime > local_mtime:
            return False, (
                f"Remote is newer (remote: {remote_mtime}, local: {local_mtime}). "
                "Use --force to override or pull first."
            )

    # Push
    result = subprocess.run(
        ["rclone", "copy", str(db_path), remote, "--progress"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, f"Pushed to {remote}"
    else:
        return False, f"Push failed: {result.stderr}"


def pull(remote: Optional[str] = None, force: bool = False) -> Tuple[bool, str]:
    """Pull database from remote.

    Args:
        remote: Remote path (e.g., "gdrive:bujo")
        force: Skip timestamp check and backup

    Returns:
        (success, message) tuple
    """
    if not check_rclone():
        return False, "rclone not installed"

    if not remote:
        config = get_sync_config()
        remote = config.get("remote")
        if not remote:
            return False, "No remote configured. Set BUJO_SYNC_REMOTE environment variable."

    db_path = get_db_path()

    # Check timestamps unless forcing
    if not force and db_path.exists():
        local_mtime = get_local_mtime()
        remote_mtime = get_remote_mtime(f"{remote}/bujo.db")

        if local_mtime and remote_mtime and local_mtime > remote_mtime:
            return False, (
                f"Local is newer (local: {local_mtime}, remote: {remote_mtime}). "
                "Use --force to override or push first."
            )

    # Create backup before overwriting
    if db_path.exists() and not force:
        try:
            backup_path = create_backup()
        except Exception as e:
            return False, f"Backup failed: {e}"

    # Pull
    result = subprocess.run(
        ["rclone", "copy", f"{remote}/bujo.db", str(db_path.parent), "--progress"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, f"Pulled from {remote}"
    else:
        return False, f"Pull failed: {result.stderr}"


def sync(remote: Optional[str] = None) -> Tuple[bool, str]:
    """Sync with remote (pull then push).

    Uses last-write-wins strategy.

    Args:
        remote: Remote path

    Returns:
        (success, message) tuple
    """
    if not check_rclone():
        return False, "rclone not installed"

    if not remote:
        config = get_sync_config()
        remote = config.get("remote")
        if not remote:
            return False, "No remote configured. Set BUJO_SYNC_REMOTE environment variable."

    local_mtime = get_local_mtime()
    remote_mtime = get_remote_mtime(f"{remote}/bujo.db")

    messages = []

    if remote_mtime is None:
        # No remote, just push
        success, msg = push(remote, force=True)
        return success, f"No remote found. {msg}"

    if local_mtime is None:
        # No local, just pull
        success, msg = pull(remote, force=True)
        return success, f"No local found. {msg}"

    # Both exist, compare timestamps
    if remote_mtime > local_mtime:
        # Remote is newer, pull
        messages.append(f"Remote is newer ({remote_mtime} > {local_mtime})")
        success, msg = pull(remote)
        messages.append(msg)
    else:
        # Local is newer or same, push
        messages.append(f"Local is newer or same ({local_mtime} >= {remote_mtime})")
        success, msg = push(remote)
        messages.append(msg)

    return success, " ".join(messages)


def list_backups() -> list:
    """List available backups."""
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("bujo_backup_*.db"), reverse=True)

    result = []
    for backup in backups:
        stat = backup.stat()
        result.append({
            "path": backup,
            "name": backup.name,
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime),
        })

    return result


def restore_backup(backup_name: str) -> Tuple[bool, str]:
    """Restore from a backup.

    Args:
        backup_name: Name of backup file to restore

    Returns:
        (success, message) tuple
    """
    backup_dir = get_backup_dir()
    backup_path = backup_dir / backup_name

    if not backup_path.exists():
        return False, f"Backup not found: {backup_name}"

    db_path = get_db_path()

    # Backup current before restoring
    if db_path.exists():
        create_backup()

    shutil.copy2(backup_path, db_path)
    return True, f"Restored from {backup_name}"


def get_sync_status(remote: Optional[str] = None) -> dict:
    """Get sync status information."""
    if not remote:
        config = get_sync_config()
        remote = config.get("remote", "")

    local_mtime = get_local_mtime()
    remote_mtime = get_remote_mtime(f"{remote}/bujo.db") if remote else None

    status = "unknown"
    if local_mtime and remote_mtime:
        if local_mtime > remote_mtime:
            status = "local_newer"
        elif remote_mtime > local_mtime:
            status = "remote_newer"
        else:
            status = "synced"
    elif local_mtime and not remote_mtime:
        status = "local_only"
    elif remote_mtime and not local_mtime:
        status = "remote_only"
    else:
        status = "none"

    return {
        "remote": remote,
        "rclone_available": check_rclone(),
        "local_mtime": local_mtime,
        "remote_mtime": remote_mtime,
        "status": status,
        "backups": len(list_backups()),
    }
