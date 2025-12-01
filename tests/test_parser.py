"""Tests for the markdown parser"""

import pytest
from clibujo.core.parser import parse_entry, generate_entry_ref
from clibujo.core.models import EntryType, TaskStatus, Signifier


class TestParseEntry:
    """Tests for parse_entry function"""

    def test_parse_open_task(self):
        entry = parse_entry("[ ] Buy groceries")
        assert entry is not None
        assert entry.entry_type == EntryType.TASK
        assert entry.status == TaskStatus.OPEN
        assert entry.content == "Buy groceries"
        assert entry.signifier is None

    def test_parse_complete_task(self):
        entry = parse_entry("[x] Done task")
        assert entry is not None
        assert entry.entry_type == EntryType.TASK
        assert entry.status == TaskStatus.COMPLETE
        assert entry.content == "Done task"

    def test_parse_migrated_task(self):
        entry = parse_entry("[>] Migrated task")
        assert entry is not None
        assert entry.entry_type == EntryType.TASK
        assert entry.status == TaskStatus.MIGRATED

    def test_parse_scheduled_task(self):
        entry = parse_entry("[<] Scheduled task")
        assert entry is not None
        assert entry.entry_type == EntryType.TASK
        assert entry.status == TaskStatus.SCHEDULED

    def test_parse_cancelled_task(self):
        entry = parse_entry("[~] Cancelled task")
        assert entry is not None
        assert entry.entry_type == EntryType.TASK
        assert entry.status == TaskStatus.CANCELLED

    def test_parse_event(self):
        entry = parse_entry("○ Meeting at 3pm")
        assert entry is not None
        assert entry.entry_type == EntryType.EVENT
        assert entry.content == "Meeting at 3pm"
        assert entry.status is None

    def test_parse_note(self):
        entry = parse_entry("- Important observation")
        assert entry is not None
        assert entry.entry_type == EntryType.NOTE
        assert entry.content == "Important observation"

    def test_parse_priority_task(self):
        entry = parse_entry("* [ ] Urgent task")
        assert entry is not None
        assert entry.entry_type == EntryType.TASK
        assert entry.signifier == Signifier.PRIORITY
        assert entry.content == "Urgent task"

    def test_parse_inspiration_note(self):
        entry = parse_entry("! - Great idea")
        assert entry is not None
        assert entry.entry_type == EntryType.NOTE
        assert entry.signifier == Signifier.INSPIRATION
        assert entry.content == "Great idea"

    def test_parse_explore_task(self):
        entry = parse_entry("? [ ] Research this")
        assert entry is not None
        assert entry.entry_type == EntryType.TASK
        assert entry.signifier == Signifier.EXPLORE

    def test_parse_migration_to_hint(self):
        entry = parse_entry("[>] Task →months/2024-12.md")
        assert entry is not None
        assert entry.status == TaskStatus.MIGRATED
        assert entry.migrated_to == "months/2024-12.md"
        assert entry.content == "Task"

    def test_parse_migration_from_hint(self):
        entry = parse_entry("[ ] Task ←daily/2024-11-15.md")
        assert entry is not None
        assert entry.migrated_from == "daily/2024-11-15.md"

    def test_parse_empty_line(self):
        entry = parse_entry("")
        assert entry is None

    def test_parse_header(self):
        entry = parse_entry("# December 3, 2024")
        assert entry is None

    def test_parse_plain_text(self):
        entry = parse_entry("Just some regular text")
        assert entry is None

    def test_parse_bare_signifier(self):
        # Bare signifier without entry marker should not parse
        entry = parse_entry("* Just an asterisk")
        assert entry is None

    def test_parse_with_custom_signifiers(self):
        entry = parse_entry("@ [ ] Waiting on response", signifiers={
            "@": "waiting",
            "*": "priority",
        })
        assert entry is not None
        assert entry.signifier == Signifier.WAITING


class TestGenerateEntryRef:
    """Tests for entry reference generation"""

    def test_generates_6_chars(self):
        ref = generate_entry_ref("daily/2024-12-03.md", "Test content", "2024-12-03")
        assert len(ref) == 6

    def test_deterministic(self):
        ref1 = generate_entry_ref("daily/2024-12-03.md", "Test content", "2024-12-03")
        ref2 = generate_entry_ref("daily/2024-12-03.md", "Test content", "2024-12-03")
        assert ref1 == ref2

    def test_different_content_different_ref(self):
        ref1 = generate_entry_ref("daily/2024-12-03.md", "Content A", "2024-12-03")
        ref2 = generate_entry_ref("daily/2024-12-03.md", "Content B", "2024-12-03")
        assert ref1 != ref2

    def test_different_file_different_ref(self):
        ref1 = generate_entry_ref("daily/2024-12-03.md", "Same content", "2024-12-03")
        ref2 = generate_entry_ref("daily/2024-12-04.md", "Same content", "2024-12-04")
        assert ref1 != ref2
