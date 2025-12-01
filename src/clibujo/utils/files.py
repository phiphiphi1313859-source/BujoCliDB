"""File I/O utilities for CLIBuJo"""

import hashlib
from datetime import date
from pathlib import Path
from typing import Generator, Optional


def ensure_data_dirs(data_dir: Path) -> None:
    """Ensure all required data directories exist"""
    dirs = [
        data_dir,
        data_dir / "daily",
        data_dir / "months",
        data_dir / "collections",
        data_dir / "collections" / "projects",
        data_dir / "collections" / "trackers",
        data_dir / "collections" / "lists",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def get_daily_file(data_dir: Path, day: date) -> Path:
    """Get path to daily log file"""
    return data_dir / "daily" / f"{day.strftime('%Y-%m-%d')}.md"


def get_monthly_file(data_dir: Path, year: int, month: int) -> Path:
    """Get path to monthly log file"""
    return data_dir / "months" / f"{year:04d}-{month:02d}.md"


def get_future_file(data_dir: Path) -> Path:
    """Get path to future log file"""
    return data_dir / "future.md"


def get_collection_file(
    data_dir: Path,
    name: str,
    collection_type: Optional[str] = None,
) -> Path:
    """Get path to collection file"""
    if collection_type:
        return data_dir / "collections" / collection_type / f"{name}.md"
    # Check if name includes type
    if "/" in name:
        parts = name.split("/", 1)
        return data_dir / "collections" / parts[0] / f"{parts[1]}.md"
    return data_dir / "collections" / f"{name}.md"


def get_index_file(data_dir: Path) -> Path:
    """Get path to index file"""
    return data_dir / "index.md"


def read_file_lines(file_path: Path) -> list[str]:
    """Read file as list of lines (preserving newlines)"""
    if not file_path.exists():
        return []
    return file_path.read_text(encoding="utf-8").splitlines(keepends=True)


def write_file_lines(file_path: Path, lines: list[str]) -> None:
    """Write lines to file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure each line ends with newline
    content = ""
    for line in lines:
        if not line.endswith("\n"):
            line += "\n"
        content += line
    file_path.write_text(content, encoding="utf-8")


def update_line(file_path: Path, line_number: int, new_content: str) -> Optional[str]:
    """Update a specific line in a file. Returns old content."""
    lines = read_file_lines(file_path)

    if line_number < 1 or line_number > len(lines):
        return None

    idx = line_number - 1
    old_content = lines[idx].rstrip("\n")
    lines[idx] = new_content.rstrip("\n") + "\n"
    write_file_lines(file_path, lines)
    return old_content


def append_line(file_path: Path, content: str) -> int:
    """Append a line to file. Returns new line number."""
    lines = read_file_lines(file_path)

    # Ensure there's a blank line before if file isn't empty
    if lines and lines[-1].strip():
        pass  # Last line has content, that's fine

    lines.append(content.rstrip("\n") + "\n")
    write_file_lines(file_path, lines)
    return len(lines)


def insert_line(file_path: Path, line_number: int, content: str) -> None:
    """Insert a line at specific position"""
    lines = read_file_lines(file_path)

    if line_number < 1:
        line_number = 1
    if line_number > len(lines) + 1:
        line_number = len(lines) + 1

    idx = line_number - 1
    lines.insert(idx, content.rstrip("\n") + "\n")
    write_file_lines(file_path, lines)


def delete_line(file_path: Path, line_number: int) -> Optional[str]:
    """Delete a line from file. Returns deleted content."""
    lines = read_file_lines(file_path)

    if line_number < 1 or line_number > len(lines):
        return None

    idx = line_number - 1
    deleted = lines.pop(idx)
    write_file_lines(file_path, lines)
    return deleted.rstrip("\n")


def hash_file(file_path: Path) -> str:
    """Compute SHA256 hash of file content"""
    if not file_path.exists():
        return ""
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def walk_markdown_files(data_dir: Path) -> Generator[Path, None, None]:
    """Walk all markdown files in data directory"""
    if not data_dir.exists():
        return

    for path in data_dir.rglob("*.md"):
        yield path


def create_daily_file(data_dir: Path, day: date) -> Path:
    """Create a new daily log file with header"""
    file_path = get_daily_file(data_dir, day)
    if not file_path.exists():
        header = f"# {day.strftime('%B %d, %Y')}\n\n"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(header, encoding="utf-8")
    return file_path


def create_monthly_file(data_dir: Path, year: int, month: int) -> Path:
    """Create a new monthly log file with calendar"""
    import calendar

    file_path = get_monthly_file(data_dir, year, month)
    if not file_path.exists():
        month_name = calendar.month_name[month]
        lines = [
            f"# {month_name} {year}\n",
            "\n",
            "## Calendar\n",
            "\n",
        ]

        # Generate calendar
        cal = calendar.Calendar(firstweekday=0)
        day_abbrs = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

        for day_num in cal.itermonthdays(year, month):
            if day_num == 0:
                continue
            day_date = date(year, month, day_num)
            weekday = day_date.weekday()
            lines.append(f"{day_num:02d} {day_abbrs[weekday]}\n")

        lines.extend([
            "\n",
            "## Tasks\n",
            "\n",
        ])

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("".join(lines), encoding="utf-8")
    return file_path


def create_future_file(data_dir: Path) -> Path:
    """Create future log file if it doesn't exist"""
    file_path = get_future_file(data_dir)
    if not file_path.exists():
        content = """# Future Log

## Someday

"""
        file_path.write_text(content, encoding="utf-8")
    return file_path


def create_collection_file(
    data_dir: Path,
    name: str,
    collection_type: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> Path:
    """Create a new collection file"""
    file_path = get_collection_file(data_dir, name, collection_type)
    if not file_path.exists():
        display_title = title or name.replace("-", " ").replace("_", " ").title()
        lines = [f"# {display_title}\n", "\n"]

        if description:
            lines.append(f"> {description}\n")
            lines.append("\n")

        if collection_type == "project":
            lines.extend([
                "## Goals\n",
                "\n",
                "## Tasks\n",
                "\n",
                "## Notes\n",
                "\n",
            ])
        elif collection_type == "tracker":
            lines.extend([
                "## Log\n",
                "\n",
            ])
        else:  # list
            lines.append("")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("".join(lines), encoding="utf-8")
    return file_path


def find_tasks_section(lines: list[str]) -> Optional[int]:
    """Find the line number of ## Tasks section"""
    for i, line in enumerate(lines):
        if line.strip().lower() == "## tasks":
            return i + 1
    return None


def append_to_section(
    file_path: Path,
    section: str,
    content: str,
) -> int:
    """Append content to a specific section, returns line number"""
    lines = read_file_lines(file_path)

    section_header = f"## {section}"
    section_start = None

    for i, line in enumerate(lines):
        if line.strip().lower() == section_header.lower():
            section_start = i
            break

    if section_start is None:
        # Section doesn't exist, append at end
        lines.append(f"\n{section_header}\n\n{content}\n")
        write_file_lines(file_path, lines)
        return len(lines)

    # Find next section or end of file
    insert_at = len(lines)
    for i in range(section_start + 1, len(lines)):
        if lines[i].startswith("## "):
            insert_at = i
            break
        # Skip empty lines, insert before them if at end of section
        if lines[i].strip() and not lines[i].startswith("#"):
            insert_at = i + 1

    # Insert the content
    lines.insert(insert_at, content.rstrip("\n") + "\n")
    write_file_lines(file_path, lines)
    return insert_at + 1
