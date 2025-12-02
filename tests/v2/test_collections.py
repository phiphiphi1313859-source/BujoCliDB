"""Tests for collection operations."""

import pytest

from clibujo_v2.core.collections import (
    create_collection,
    get_collection,
    get_collection_by_name,
    get_all_collections,
    update_collection,
    archive_collection,
    unarchive_collection,
    delete_collection,
    get_collection_stats,
    search_collections,
)
from clibujo_v2.core.entries import create_entry


class TestCreateCollection:
    """Tests for collection creation."""

    def test_create_project(self, db_connection):
        """Create a project collection."""
        coll = create_collection("My Project", "project", "A test project", conn=db_connection)

        assert coll.id is not None
        assert coll.name == "My Project"
        assert coll.type == "project"
        assert coll.description == "A test project"

    def test_create_tracker(self, db_connection):
        """Create a tracker collection."""
        coll = create_collection("Expenses", "tracker", conn=db_connection)

        assert coll.type == "tracker"

    def test_create_list(self, db_connection):
        """Create a list collection."""
        coll = create_collection("Reading List", "list", conn=db_connection)

        assert coll.type == "list"

    def test_create_duplicate_name(self, db_connection):
        """Creating duplicate name should fail."""
        create_collection("Unique Name", conn=db_connection)

        with pytest.raises(Exception):
            create_collection("Unique Name", conn=db_connection)

    def test_create_case_insensitive_duplicate(self, db_connection):
        """Names should be case-insensitive unique."""
        create_collection("Test Collection", conn=db_connection)

        with pytest.raises(Exception):
            create_collection("test collection", conn=db_connection)


class TestGetCollection:
    """Tests for retrieving collections."""

    def test_get_by_id(self, sample_collection):
        """Get collection by ID."""
        coll = get_collection(sample_collection.id)

        assert coll is not None
        assert coll.name == "Test Project"

    def test_get_by_name(self, sample_collection):
        """Get collection by name."""
        coll = get_collection_by_name("Test Project")

        assert coll is not None
        assert coll.id == sample_collection.id

    def test_get_by_name_case_insensitive(self, sample_collection):
        """Get collection by name is case insensitive."""
        coll = get_collection_by_name("test project")

        assert coll is not None
        assert coll.id == sample_collection.id

    def test_get_nonexistent(self, db_connection):
        """Get non-existent collection."""
        coll = get_collection(9999)
        assert coll is None

        coll = get_collection_by_name("Does Not Exist")
        assert coll is None


class TestGetAllCollections:
    """Tests for listing collections."""

    def test_get_all(self, db_connection):
        """Get all collections."""
        create_collection("Project 1", "project", conn=db_connection)
        create_collection("Tracker 1", "tracker", conn=db_connection)
        create_collection("List 1", "list", conn=db_connection)

        colls = get_all_collections()

        assert len(colls) == 3

    def test_filter_by_type(self, db_connection):
        """Filter collections by type."""
        create_collection("Project 1", "project", conn=db_connection)
        create_collection("Tracker 1", "tracker", conn=db_connection)

        projects = get_all_collections(collection_type="project")

        assert len(projects) == 1
        assert projects[0].type == "project"

    def test_exclude_archived(self, db_connection):
        """Exclude archived collections by default."""
        coll = create_collection("Archived Project", conn=db_connection)
        archive_collection(coll.id, conn=db_connection)
        create_collection("Active Project", conn=db_connection)

        colls = get_all_collections()

        assert len(colls) == 1
        assert colls[0].name == "Active Project"

    def test_include_archived(self, db_connection):
        """Include archived when requested."""
        coll = create_collection("Archived Project", conn=db_connection)
        archive_collection(coll.id, conn=db_connection)
        create_collection("Active Project", conn=db_connection)

        colls = get_all_collections(include_archived=True)

        assert len(colls) == 2


class TestUpdateCollection:
    """Tests for updating collections."""

    def test_update_name(self, sample_collection):
        """Update collection name."""
        coll = update_collection(sample_collection.id, name="New Name")

        assert coll.name == "New Name"

    def test_update_description(self, sample_collection):
        """Update collection description."""
        coll = update_collection(sample_collection.id, description="New description")

        assert coll.description == "New description"


class TestArchiveCollection:
    """Tests for archiving collections."""

    def test_archive(self, sample_collection):
        """Archive a collection."""
        coll = archive_collection(sample_collection.id)

        assert coll.is_archived is True
        assert coll.archived_at is not None

    def test_unarchive(self, sample_collection):
        """Unarchive a collection."""
        archive_collection(sample_collection.id)
        coll = unarchive_collection(sample_collection.id)

        assert coll.is_archived is False
        assert coll.archived_at is None


class TestDeleteCollection:
    """Tests for deleting collections."""

    def test_delete_empty(self, sample_collection):
        """Delete an empty collection."""
        result = delete_collection(sample_collection.id)

        assert result is True
        assert get_collection(sample_collection.id) is None

    def test_delete_with_entries_unlink(self, sample_collection, db_connection):
        """Delete collection and unlink entries."""
        entry = create_entry("Task", collection_id=sample_collection.id, conn=db_connection)

        delete_collection(sample_collection.id, delete_entries=False, conn=db_connection)

        # Entry should still exist but unlinked
        from clibujo_v2.core.entries import get_entry
        entry = get_entry(entry.id, conn=db_connection)
        assert entry is not None
        assert entry.collection_id is None

    def test_delete_with_entries_cascade(self, sample_collection, db_connection):
        """Delete collection and its entries."""
        entry = create_entry("Task", collection_id=sample_collection.id, conn=db_connection)
        entry_id = entry.id

        delete_collection(sample_collection.id, delete_entries=True, conn=db_connection)

        from clibujo_v2.core.entries import get_entry
        assert get_entry(entry_id, conn=db_connection) is None


class TestCollectionStats:
    """Tests for collection statistics."""

    def test_empty_stats(self, sample_collection):
        """Stats for empty collection."""
        stats = get_collection_stats(sample_collection.id)

        assert stats["total"] == 0
        assert stats["tasks"] == 0

    def test_stats_with_entries(self, sample_collection, db_connection):
        """Stats with various entries."""
        create_entry("Task 1", entry_type="task", collection_id=sample_collection.id, conn=db_connection)
        create_entry("Task 2", entry_type="task", collection_id=sample_collection.id, status="complete", conn=db_connection)
        create_entry("Event", entry_type="event", collection_id=sample_collection.id, conn=db_connection)
        create_entry("Note", entry_type="note", collection_id=sample_collection.id, conn=db_connection)

        stats = get_collection_stats(sample_collection.id, conn=db_connection)

        assert stats["total"] == 4
        assert stats["tasks"] == 2
        assert stats["open"] == 1
        assert stats["complete"] == 1


class TestSearchCollections:
    """Tests for searching collections."""

    def test_search_by_name(self, db_connection):
        """Search collections by name."""
        create_collection("Project Alpha", conn=db_connection)
        create_collection("Project Beta", conn=db_connection)
        create_collection("Something Else", conn=db_connection)

        results = search_collections("Project")

        assert len(results) == 2
