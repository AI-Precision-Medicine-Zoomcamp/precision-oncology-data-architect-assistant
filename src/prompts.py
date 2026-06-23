"""
Prompt template manager.

Loads YAML templates and provides them to the RAG pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from loguru import logger

from src.config import settings


class PromptManager:
    """Manages prompt templates loaded from a YAML file."""

    def __init__(self, prompts_path: Optional[Path] = None) -> None:
        self._prompts_path = prompts_path or Path("prompts/system_prompts.yaml")
        self._templates: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load prompts from YAML file."""
        if not self._prompts_path.exists():
            logger.warning("Prompts file not found: {}", self._prompts_path)
            return
        with open(self._prompts_path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            logger.warning("Invalid prompts file format (expected dict)")
            return
        for key, value in data.items():
            if isinstance(value, str):
                self._templates[key] = value
        logger.info("Loaded {} prompt template(s)", len(self._templates))

    def get(self, name: str) -> str:
        """Get a prompt template by name. Raises KeyError if missing."""
        if name not in self._templates:
            raise KeyError(f"Prompt template '{name}' not found. Available: {list(self._templates.keys())}")
        return self._templates[name]

    def list_templates(self) -> list[str]:
        """Return list of available template names."""
        return list(self._templates.keys())

    def reload(self) -> None:
        """Reload prompts from disk."""
        self._templates.clear()
        self._load()
