"""Utility functions for CLIBuJo"""

from .files import (
    ensure_data_dirs,
    get_daily_file,
    get_monthly_file,
    get_future_file,
    get_collection_file,
    get_index_file,
    read_file_lines,
    write_file_lines,
    update_line,
    append_line,
    insert_line,
    delete_line,
    hash_file,
    walk_markdown_files,
)
from .dates import (
    parse_date,
    format_date,
    format_short_date,
    get_month_name,
    get_week_dates,
    get_month_calendar,
)
from .display import (
    get_terminal_width,
    truncate,
    is_narrow_terminal,
)

__all__ = [
    # Files
    "ensure_data_dirs",
    "get_daily_file",
    "get_monthly_file",
    "get_future_file",
    "get_collection_file",
    "get_index_file",
    "read_file_lines",
    "write_file_lines",
    "update_line",
    "append_line",
    "insert_line",
    "delete_line",
    "hash_file",
    "walk_markdown_files",
    # Dates
    "parse_date",
    "format_date",
    "format_short_date",
    "get_month_name",
    "get_week_dates",
    "get_month_calendar",
    # Display
    "get_terminal_width",
    "truncate",
    "is_narrow_terminal",
]
