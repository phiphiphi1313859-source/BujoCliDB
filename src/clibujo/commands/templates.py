"""Collection templates for CLIBuJo"""

from pathlib import Path
from typing import Optional

from ..core.config import Config

# Default templates
DEFAULT_TEMPLATES = {
    "project": """# {title}

> {description}

## Goals

-

## Tasks

## Notes

""",
    "tracker": """# {title}

> {description}

## Log

""",
    "list": """# {title}

> {description}

""",
    "reading": """# Reading List

> Books to read

## Currently Reading

## To Read

## Completed

""",
    "habit": """# {title} Tracker

> Track daily habits

## Habits

- [ ]

## Log

""",
    "goal": """# {title}

> {description}

## Objective

## Key Results

- [ ]

## Progress

## Notes

""",
}


def get_template(
    config: Config,
    template_name: str,
    title: str = "Untitled",
    description: str = "",
) -> str:
    """Get a template by name, with variable substitution"""
    # Check config for custom templates first
    template = config.templates.get(template_name)

    # Fall back to defaults
    if not template:
        template = DEFAULT_TEMPLATES.get(template_name)

    # Fall back to basic project template
    if not template:
        template = DEFAULT_TEMPLATES["project"]

    # Substitute variables
    return template.format(
        title=title,
        description=description or "Description here",
    )


def list_templates(config: Config) -> list[str]:
    """List available template names"""
    templates = set(DEFAULT_TEMPLATES.keys())
    templates.update(config.templates.keys())
    return sorted(templates)


def create_from_template(
    config: Config,
    output_path: Path,
    template_name: str,
    title: str,
    description: str = "",
) -> None:
    """Create a new file from a template"""
    content = get_template(config, template_name, title, description)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
