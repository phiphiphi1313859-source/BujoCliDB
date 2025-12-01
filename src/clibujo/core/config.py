"""Configuration management for CLIBuJo"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SyncConfig:
    """Git sync configuration"""
    enabled: bool = True
    remote: str = "origin"
    branch: str = "main"
    auto_pull: bool = True
    auto_push: bool = False


@dataclass
class IndexConfig:
    """Indexing configuration"""
    auto_reindex: bool = True
    reindex_on_sync: bool = True


@dataclass
class Config:
    """Main configuration for CLIBuJo"""
    # Paths
    bujo_dir: Path = field(default_factory=lambda: Path.home() / ".bujo")
    data_dir: Path = field(default_factory=lambda: Path.home() / ".bujo" / "data")
    cache_db: Path = field(default_factory=lambda: Path.home() / ".bujo" / "cache.db")
    config_file: Path = field(default_factory=lambda: Path.home() / ".bujo" / "config.yaml")

    # Editor
    editor: str = "vim"

    # Date formats
    date_format: str = "%B %d, %Y"  # December 03, 2024
    short_date: str = "%b %d"  # Dec 03

    # Week settings
    week_start: int = 0  # 0=Monday, 6=Sunday

    # Display settings
    narrow_threshold: int = 60
    show_entry_refs: bool = False

    # Sync settings
    sync: SyncConfig = field(default_factory=SyncConfig)

    # Index settings
    index: IndexConfig = field(default_factory=IndexConfig)

    # Collection types
    collection_types: list[str] = field(default_factory=lambda: ["project", "tracker", "list"])

    # Signifiers (char -> name mapping)
    signifiers: dict[str, str] = field(default_factory=lambda: {
        "*": "priority",
        "!": "inspiration",
        "?": "explore",
    })

    # Templates
    templates: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure paths are Path objects"""
        if isinstance(self.bujo_dir, str):
            self.bujo_dir = Path(self.bujo_dir)
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        if isinstance(self.cache_db, str):
            self.cache_db = Path(self.cache_db)
        if isinstance(self.config_file, str):
            self.config_file = Path(self.config_file)


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file"""
    config = Config()

    # Check environment variable for custom location
    if config_path is None:
        env_path = os.environ.get("BUJO_DIR")
        if env_path:
            config.bujo_dir = Path(env_path)
            config.data_dir = config.bujo_dir / "data"
            config.cache_db = config.bujo_dir / "cache.db"
            config.config_file = config.bujo_dir / "config.yaml"
        config_path = config.config_file

    if not config_path.exists():
        return config

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return config

    # Apply loaded values
    if "editor" in data:
        config.editor = data["editor"]
    if "date_format" in data:
        config.date_format = data["date_format"]
    if "short_date" in data:
        config.short_date = data["short_date"]
    if "week_start" in data:
        config.week_start = data["week_start"]
    if "narrow_threshold" in data:
        config.narrow_threshold = data["narrow_threshold"]
    if "show_entry_refs" in data:
        config.show_entry_refs = data["show_entry_refs"]

    # Sync settings
    if "sync" in data:
        sync_data = data["sync"]
        config.sync = SyncConfig(
            enabled=sync_data.get("enabled", True),
            remote=sync_data.get("remote", "origin"),
            branch=sync_data.get("branch", "main"),
            auto_pull=sync_data.get("auto_pull", True),
            auto_push=sync_data.get("auto_push", False),
        )

    # Index settings
    if "index" in data:
        index_data = data["index"]
        config.index = IndexConfig(
            auto_reindex=index_data.get("auto_reindex", True),
            reindex_on_sync=index_data.get("reindex_on_sync", True),
        )

    # Collection types
    if "collection_types" in data:
        config.collection_types = data["collection_types"]

    # Signifiers (merge with defaults)
    if "signifiers" in data:
        config.signifiers.update(data["signifiers"])

    # Templates
    if "templates" in data:
        config.templates = data["templates"]

    return config


def save_config(config: Config) -> None:
    """Save configuration to YAML file"""
    data = {
        "editor": config.editor,
        "date_format": config.date_format,
        "short_date": config.short_date,
        "week_start": config.week_start,
        "narrow_threshold": config.narrow_threshold,
        "show_entry_refs": config.show_entry_refs,
        "sync": {
            "enabled": config.sync.enabled,
            "remote": config.sync.remote,
            "branch": config.sync.branch,
            "auto_pull": config.sync.auto_pull,
            "auto_push": config.sync.auto_push,
        },
        "index": {
            "auto_reindex": config.index.auto_reindex,
            "reindex_on_sync": config.index.reindex_on_sync,
        },
        "collection_types": config.collection_types,
        "signifiers": config.signifiers,
    }

    if config.templates:
        data["templates"] = config.templates

    config.config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config.config_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_default_config_yaml() -> str:
    """Return default config as YAML string"""
    return """# CLIBuJo Configuration

# Editor for full-page editing
editor: vim

# Date format
date_format: "%B %d, %Y"  # December 03, 2024
short_date: "%b %d"       # Dec 03

# First day of week (0=Monday, 6=Sunday)
week_start: 0

# Display
narrow_threshold: 60      # Use compact mode below this width
show_entry_refs: false    # Show [a3f2c1] refs (true) or [1] indices (false)

# Sync settings
sync:
  enabled: true
  remote: origin
  branch: main
  auto_pull: true         # Pull on startup
  auto_push: false        # Require explicit sync

# Index settings
index:
  auto_reindex: true      # Incremental reindex on startup
  reindex_on_sync: true   # Reindex after git pull

# Default collection types
collection_types:
  - project
  - tracker
  - list

# Custom signifiers (extend defaults: * ! ?)
# signifiers:
#   "@": "waiting"
#   "#": "delegated"
"""
