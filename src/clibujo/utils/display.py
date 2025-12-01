"""Display utilities for CLIBuJo"""

import shutil


def get_terminal_width() -> int:
    """Get terminal width with sensible default"""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def get_terminal_height() -> int:
    """Get terminal height with sensible default"""
    try:
        return shutil.get_terminal_size().lines
    except Exception:
        return 24


def is_narrow_terminal(threshold: int = 60) -> bool:
    """Check if terminal is narrow"""
    return get_terminal_width() < threshold


def truncate(text: str, max_width: int, suffix: str = "...") -> str:
    """Truncate text with suffix if too long"""
    if len(text) <= max_width:
        return text
    if max_width <= len(suffix):
        return suffix[:max_width]
    return text[: max_width - len(suffix)] + suffix


def pad_right(text: str, width: int, char: str = " ") -> str:
    """Pad text to width on right"""
    if len(text) >= width:
        return text[:width]
    return text + char * (width - len(text))


def pad_left(text: str, width: int, char: str = " ") -> str:
    """Pad text to width on left"""
    if len(text) >= width:
        return text[:width]
    return char * (width - len(text)) + text


def center(text: str, width: int, char: str = " ") -> str:
    """Center text in width"""
    if len(text) >= width:
        return text[:width]
    left_pad = (width - len(text)) // 2
    right_pad = width - len(text) - left_pad
    return char * left_pad + text + char * right_pad
