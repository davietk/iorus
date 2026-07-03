from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = "config.yaml"


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    if "connectors" not in raw:
        raw["connectors"] = []

    raw.setdefault("app", {})
    raw.setdefault("display", {})
    raw.setdefault("mqtt", {})

    return raw
