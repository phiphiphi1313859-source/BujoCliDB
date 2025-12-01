"""Indexing logic for CLIBuJo"""

from pathlib import Path
from typing import Optional

from .config import Config
from .database import Database
from .parser import determine_context, generate_entry_ref, parse_file
from ..utils.files import hash_file, walk_markdown_files


class Indexer:
    """Handles indexing of markdown files into SQLite"""

    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db

    def full_reindex(self) -> int:
        """Rebuild entire SQLite cache from markdown files. Returns count of files indexed."""
        self.db.clear_entries()

        count = 0
        for md_file in walk_markdown_files(self.config.data_dir):
            self._index_file(md_file)
            count += 1

        return count

    def incremental_reindex(self) -> int:
        """Only reindex files that changed. Returns count of files reindexed."""
        if not self.config.data_dir.exists():
            return 0

        indexed_files = set(self.db.get_all_indexed_files())
        current_files = set()
        changed_count = 0

        # Check for new or modified files
        for md_file in walk_markdown_files(self.config.data_dir):
            rel_path = self._get_relative_path(md_file)
            current_files.add(rel_path)

            current_hash = hash_file(md_file)
            stored_hash = self.db.get_file_hash(rel_path)

            if current_hash != stored_hash:
                # File is new or modified
                self.db.clear_file_entries(rel_path)
                self._index_file(md_file)
                self.db.set_file_hash(rel_path, current_hash)
                changed_count += 1

        # Remove entries for deleted files
        deleted_files = indexed_files - current_files
        for deleted_file in deleted_files:
            self.db.clear_file_entries(deleted_file)
            self.db.delete_file_hash(deleted_file)
            changed_count += 1

        return changed_count

    def reindex_file(self, file_path: Path) -> None:
        """Reindex a single file"""
        rel_path = self._get_relative_path(file_path)
        self.db.clear_file_entries(rel_path)

        if file_path.exists():
            self._index_file(file_path)
            self.db.set_file_hash(rel_path, hash_file(file_path))
        else:
            self.db.delete_file_hash(rel_path)

    def _index_file(self, file_path: Path) -> None:
        """Parse and index a single markdown file"""
        context = determine_context(file_path, self.config.data_dir)
        rel_path = self._get_relative_path(file_path)

        entries = parse_file(file_path, self.config.signifiers)

        for entry in entries:
            # Generate stable reference
            entry_date_str = str(context.date) if context.date else ""
            entry_ref = generate_entry_ref(rel_path, entry.content, entry_date_str)

            # Handle potential duplicates (same content, same file, same date)
            # by appending line number
            existing = self.db.get_entry_by_ref(entry_ref)
            if existing:
                entry_ref = generate_entry_ref(
                    rel_path, entry.content, f"{entry_date_str}:{entry.line_number}"
                )

            self.db.insert_entry(
                entry_ref=entry_ref,
                source_file=rel_path,
                line_number=entry.line_number,
                raw_line=entry.raw_line,
                entry_type=entry.entry_type.value,
                content=entry.content,
                status=entry.status.value if entry.status else None,
                signifier=entry.signifier.value if entry.signifier else None,
                entry_date=context.date,
                collection=context.collection,
                month=context.month,
                migrated_to=entry.migrated_to,
                migrated_from=entry.migrated_from,
            )

        # Update file hash
        self.db.set_file_hash(rel_path, hash_file(file_path))

    def _get_relative_path(self, file_path: Path) -> str:
        """Get relative path from data directory"""
        try:
            return str(file_path.relative_to(self.config.data_dir))
        except ValueError:
            return str(file_path)


def init_bujo(config: Config) -> tuple[Database, Indexer]:
    """Initialize database and indexer"""
    db = Database(config.cache_db)
    db.init_schema()
    indexer = Indexer(config, db)
    return db, indexer


def startup_reindex(config: Config, db: Database, indexer: Indexer) -> int:
    """Perform startup reindex based on config"""
    if not config.cache_db.exists():
        # First run - full reindex
        return indexer.full_reindex()
    elif config.index.auto_reindex:
        # Incremental reindex
        return indexer.incremental_reindex()
    return 0
