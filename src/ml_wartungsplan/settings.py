from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_yaml(path: str | Path) -> dict[str, Any]:
    resolved = resolve_project_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Configuration file not found: {resolved}")
    with resolved.open("r", encoding="utf-8") as file:
        content = yaml.safe_load(file)
    return content or {}


def load_settings() -> dict[str, Any]:
    settings_path = os.getenv("MLW_SETTINGS_PATH", "config/settings.yaml")
    return load_yaml(settings_path)


def load_guardrails() -> dict[str, Any]:
    guardrails_path = os.getenv("MLW_GUARDRAILS_PATH", "config/guardrails.yaml")
    return load_yaml(guardrails_path)
