"""Git sync commands for CLIBuJo"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core.config import Config
from ..core.database import Database
from ..core.indexer import Indexer

console = Console()


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", "Git not found"
    except Exception as e:
        return 1, "", str(e)


def git_pull(config: Config) -> bool:
    """Pull from remote"""
    if not config.sync.enabled:
        return True

    code, stdout, stderr = run_git(
        ["pull", "--rebase", config.sync.remote, config.sync.branch],
        config.bujo_dir
    )

    return code == 0


def has_conflicts(config: Config) -> bool:
    """Check if there are merge conflicts"""
    code, stdout, stderr = run_git(["diff", "--check"], config.bujo_dir)
    return code != 0 or "conflict" in stdout.lower()


def get_conflicted_files(config: Config) -> list[str]:
    """Get list of files with conflicts"""
    code, stdout, stderr = run_git(
        ["diff", "--name-only", "--diff-filter=U"],
        config.bujo_dir
    )
    if code == 0 and stdout.strip():
        return stdout.strip().split("\n")
    return []


def has_changes(config: Config) -> bool:
    """Check if there are uncommitted changes"""
    code, stdout, stderr = run_git(["status", "--porcelain"], config.bujo_dir)
    return bool(stdout.strip())


def get_device_name() -> str:
    """Get a device identifier for commit messages"""
    import socket
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def do_sync(config: Config, db: Database, indexer: Indexer):
    """Perform full sync operation"""
    if not config.sync.enabled:
        console.print("[yellow]Sync is disabled in config[/yellow]")
        return

    console.print()
    console.print("[bold]Syncing...[/bold]")

    # Check if git repo exists
    git_dir = config.bujo_dir / ".git"
    if not git_dir.exists():
        console.print("[red]Not a git repository. Run 'bujo init' first.[/red]")
        return

    # Pull
    console.print("  Pulling from remote...")
    code, stdout, stderr = run_git(
        ["pull", "--rebase", config.sync.remote, config.sync.branch],
        config.bujo_dir
    )

    if code != 0:
        if "conflict" in stderr.lower() or "conflict" in stdout.lower():
            conflicted = get_conflicted_files(config)
            console.print(f"[red]Conflicts detected in {len(conflicted)} file(s):[/red]")
            for f in conflicted:
                console.print(f"    - {f}")
            console.print()
            console.print("[yellow]Resolve conflicts manually, then run 'bujo sync' again.[/yellow]")
            return
        elif "Could not read from remote" in stderr or "Could not resolve" in stderr:
            console.print("[yellow]Could not reach remote (offline?)[/yellow]")
        else:
            # Might just be nothing to pull
            pass

    # Check for conflicts
    if has_conflicts(config):
        conflicted = get_conflicted_files(config)
        console.print(f"[red]Conflicts detected in {len(conflicted)} file(s):[/red]")
        for f in conflicted:
            console.print(f"    - {f}")
        console.print()
        console.print("[yellow]Resolve conflicts manually, then run 'bujo sync' again.[/yellow]")
        return

    console.print("  [green]✓[/green] Pulled")

    # Reindex changed files
    console.print("  Reindexing...")
    changed = indexer.incremental_reindex()
    if changed > 0:
        console.print(f"  [green]✓[/green] Reindexed {changed} file(s)")
    else:
        console.print("  [green]✓[/green] No changes to reindex")

    # Stage changes
    if has_changes(config):
        console.print("  Staging changes...")
        run_git(["add", "-A"], config.bujo_dir)

        # Commit
        device = get_device_name()
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        commit_msg = f"sync: {device} {timestamp}"

        code, stdout, stderr = run_git(["commit", "-m", commit_msg], config.bujo_dir)
        if code == 0:
            console.print(f'  [green]✓[/green] Committed: "{commit_msg}"')

        # Push
        console.print("  Pushing to remote...")
        code, stdout, stderr = run_git(
            ["push", config.sync.remote, config.sync.branch],
            config.bujo_dir
        )

        if code == 0:
            console.print("  [green]✓[/green] Pushed")
        else:
            if "Could not read from remote" in stderr or "Could not resolve" in stderr:
                console.print("  [yellow]Could not push (offline?). Changes committed locally.[/yellow]")
            else:
                console.print(f"  [red]Push failed: {stderr}[/red]")
    else:
        console.print("  [dim]No local changes to commit[/dim]")

    console.print()
    console.print("[green]Sync complete![/green]")
    console.print()
