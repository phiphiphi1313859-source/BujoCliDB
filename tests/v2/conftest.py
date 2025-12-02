"""Pytest configuration and fixtures for CLIBuJo v2 tests."""

import os
import tempfile
from pathlib import Path

import pytest

# Set test database path before any imports
@pytest.fixture(autouse=True)
def test_db_env(tmp_path):
    """Set BUJO_DIR to a temp directory for each test."""
    test_dir = tmp_path / "bujo_test"
    test_dir.mkdir()
    old_env = os.environ.get("BUJO_DIR")
    os.environ["BUJO_DIR"] = str(test_dir)
    yield test_dir
    if old_env is not None:
        os.environ["BUJO_DIR"] = old_env
    else:
        del os.environ["BUJO_DIR"]


@pytest.fixture
def db_connection(test_db_env):
    """Get a database connection for tests."""
    from clibujo_v2.core.db import get_connection, init_db

    init_db()
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture
def sample_entries(db_connection):
    """Create sample entries for testing."""
    from clibujo_v2.core.entries import create_entry

    entries = [
        create_entry("Buy groceries", entry_type="task", entry_date="2025-01-15", conn=db_connection),
        create_entry("Meeting at 2pm", entry_type="event", entry_date="2025-01-15", conn=db_connection),
        create_entry("Remember to call John", entry_type="note", entry_date="2025-01-15", conn=db_connection),
        create_entry("Important task", entry_type="task", entry_date="2025-01-15", signifier="priority", conn=db_connection),
    ]
    return entries


@pytest.fixture
def sample_collection(db_connection):
    """Create a sample collection for testing."""
    from clibujo_v2.core.collections import create_collection

    return create_collection("Test Project", "project", "A test project", conn=db_connection)


@pytest.fixture
def sample_habits(db_connection):
    """Create sample habits for testing."""
    from clibujo_v2.core.habits import create_habit

    habits = [
        create_habit("Exercise", "daily", conn=db_connection),
        create_habit("Read", "weekly:3", conn=db_connection),
        create_habit("Meditate", "days:mon,wed,fri", conn=db_connection),
    ]
    return habits
