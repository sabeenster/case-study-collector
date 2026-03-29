"""Configuration loader for Case Study Collector."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GenerationConfig:
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4000


@dataclass
class StorageConfig:
    db_path: str = "data/casestudies.db"
    uploads_dir: str = "uploads"


@dataclass
class AppConfig:
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

    @property
    def anthropic_api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def resend_api_key(self) -> str:
        return os.getenv("RESEND_API_KEY", "")

    @property
    def resend_from_email(self) -> str:
        return os.getenv("RESEND_FROM_EMAIL", "")

    @property
    def resend_to_email(self) -> list[str]:
        raw = os.getenv("RESEND_TO_EMAIL", "")
        return [e.strip() for e in raw.split(",") if e.strip()]

    @property
    def db_path(self) -> Path:
        return Path(self.storage.db_path)

    @property
    def uploads_path(self) -> Path:
        return Path(self.storage.uploads_dir)

    def ensure_dirs(self) -> None:
        """Create data and upload directories if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.uploads_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "AppConfig":
        """Load config from YAML file, falling back to defaults."""
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        config = cls()

        g_raw = raw.get("generation", {})
        config.generation = GenerationConfig(
            model=g_raw.get("model", config.generation.model),
            max_tokens=g_raw.get("max_tokens", config.generation.max_tokens),
        )

        s_raw = raw.get("storage", {})
        config.storage = StorageConfig(
            db_path=s_raw.get("db_path", config.storage.db_path),
            uploads_dir=s_raw.get("uploads_dir", config.storage.uploads_dir),
        )

        return config
