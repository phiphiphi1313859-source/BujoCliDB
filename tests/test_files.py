"""Tests for file utilities"""

import pytest
import tempfile
from datetime import date
from pathlib import Path

from clibujo.utils.files import (
    ensure_data_dirs,
    get_daily_file,
    get_monthly_file,
    get_future_file,
    get_collection_file,
    read_file_lines,
    write_file_lines,
    update_line,
    append_line,
    delete_line,
    hash_file,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestFileUtils:
    """Tests for file utilities"""

    def test_ensure_data_dirs(self, temp_dir):
        """Test directory creation"""
        ensure_data_dirs(temp_dir)

        assert (temp_dir / "daily").exists()
        assert (temp_dir / "months").exists()
        assert (temp_dir / "collections").exists()
        assert (temp_dir / "collections" / "projects").exists()

    def test_get_daily_file(self, temp_dir):
        """Test daily file path generation"""
        path = get_daily_file(temp_dir, date(2024, 12, 3))
        assert path == temp_dir / "daily" / "2024-12-03.md"

    def test_get_monthly_file(self, temp_dir):
        """Test monthly file path generation"""
        path = get_monthly_file(temp_dir, 2024, 12)
        assert path == temp_dir / "months" / "2024-12.md"

    def test_get_future_file(self, temp_dir):
        """Test future file path generation"""
        path = get_future_file(temp_dir)
        assert path == temp_dir / "future.md"

    def test_get_collection_file(self, temp_dir):
        """Test collection file path generation"""
        path = get_collection_file(temp_dir, "myproject", "projects")
        assert path == temp_dir / "collections" / "projects" / "myproject.md"

    def test_get_collection_file_with_slash(self, temp_dir):
        """Test collection file path with type in name"""
        path = get_collection_file(temp_dir, "projects/myproject")
        assert path == temp_dir / "collections" / "projects" / "myproject.md"

    def test_read_write_file_lines(self, temp_dir):
        """Test reading and writing file lines"""
        file_path = temp_dir / "test.md"
        lines = ["Line 1\n", "Line 2\n", "Line 3\n"]

        write_file_lines(file_path, lines)
        read_lines = read_file_lines(file_path)

        assert len(read_lines) == 3
        assert "Line 1" in read_lines[0]

    def test_update_line(self, temp_dir):
        """Test updating a specific line"""
        file_path = temp_dir / "test.md"
        write_file_lines(file_path, ["Line 1", "Line 2", "Line 3"])

        old = update_line(file_path, 2, "Updated Line 2")
        assert old == "Line 2"

        lines = read_file_lines(file_path)
        assert "Updated" in lines[1]

    def test_append_line(self, temp_dir):
        """Test appending a line"""
        file_path = temp_dir / "test.md"
        write_file_lines(file_path, ["Line 1", "Line 2"])

        new_line_num = append_line(file_path, "Line 3")
        assert new_line_num == 3

        lines = read_file_lines(file_path)
        assert len(lines) == 3

    def test_delete_line(self, temp_dir):
        """Test deleting a line"""
        file_path = temp_dir / "test.md"
        write_file_lines(file_path, ["Line 1", "Line 2", "Line 3"])

        deleted = delete_line(file_path, 2)
        assert deleted == "Line 2"

        lines = read_file_lines(file_path)
        assert len(lines) == 2

    def test_hash_file(self, temp_dir):
        """Test file hashing"""
        file_path = temp_dir / "test.md"
        file_path.write_text("Test content")

        hash1 = hash_file(file_path)
        assert len(hash1) == 64  # SHA256 hex

        # Same content = same hash
        hash2 = hash_file(file_path)
        assert hash1 == hash2

        # Different content = different hash
        file_path.write_text("Different content")
        hash3 = hash_file(file_path)
        assert hash1 != hash3

    def test_hash_nonexistent_file(self, temp_dir):
        """Test hashing nonexistent file"""
        file_path = temp_dir / "nonexistent.md"
        hash_value = hash_file(file_path)
        assert hash_value == ""
