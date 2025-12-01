"""Editor integration for CLIBuJo"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core.config import Config

console = Console()


def get_editor(config: Config) -> str:
    """Get the editor command to use"""
    # Check environment variables first
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        return editor

    # Fall back to config
    return config.editor


def open_in_editor(
    config: Config,
    file_path: Path,
    line_number: Optional[int] = None,
):
    """Open a file in the user's editor"""
    editor = get_editor(config)

    # Ensure file exists
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

    # Build command
    cmd = [editor]

    # Add line number argument for common editors
    if line_number:
        editor_name = os.path.basename(editor).lower()
        if editor_name in ("vim", "nvim", "vi"):
            cmd.append(f"+{line_number}")
        elif editor_name in ("nano",):
            cmd.append(f"+{line_number}")
        elif editor_name in ("emacs", "emacsclient"):
            cmd.append(f"+{line_number}")
        elif editor_name in ("code", "code-insiders"):
            cmd.extend(["--goto", f"{file_path}:{line_number}"])
            file_path = None  # Already included in goto
        elif editor_name in ("subl", "sublime"):
            cmd.append(f"{file_path}:{line_number}")
            file_path = None

    if file_path:
        cmd.append(str(file_path))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Editor exited with error: {e.returncode}[/red]")
    except FileNotFoundError:
        console.print(f"[red]Editor not found: {editor}[/red]")
        console.print("[dim]Set $EDITOR or update config.yaml[/dim]")
    except Exception as e:
        console.print(f"[red]Error opening editor: {e}[/red]")
