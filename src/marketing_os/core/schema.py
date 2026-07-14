from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any


def assets_root() -> Path:
    return Path(str(resources.files("marketing_os").joinpath("assets")))


def template_root() -> Path:
    return assets_root() / "business-template"


def skills_root() -> Path:
    return assets_root() / "skills"


def load_schema() -> dict[str, Any]:
    return json.loads((assets_root() / "schema.json").read_text(encoding="utf-8"))


def read_config(root: Path) -> dict[str, Any] | None:
    path = root / ".mos" / "config.yaml"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def config_text(name: str) -> str:
    payload = {
        "schema": "mos.business-repo.v1",
        "schema_version": 1,
        "business_name": name.strip(),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "business"
