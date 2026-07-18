from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

from marketing_os.core.results import finding

MODES = ("in-house", "agency", "client")


def assets_root() -> Path:
    return Path(str(resources.files("marketing_os").joinpath("assets")))


def template_root() -> Path:
    return assets_root() / "business-template"


def overlay_root() -> Path:
    return assets_root() / "mode-overlays"


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


def find_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".mos" / "config.yaml").is_file():
            return candidate
    return None


def config_text(name: str, *, mode: str | None = None, agency: str | None = None) -> str:
    payload: dict[str, Any] = {
        "schema": "mos.business-repo.v1",
        "schema_version": 1,
        "business_name": name.strip(),
    }
    if mode is not None:
        payload["mode"] = mode
    if agency is not None and agency.strip():
        payload["agency"] = agency.strip()
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def repo_mode(config: dict[str, Any] | None) -> tuple[str, list[dict[str, str]]]:
    """Resolve the repository mode and any read findings.

    Missing ``mode`` implies ``in-house`` with a warning (legacy repo). A present
    but unrecognized value fails closed with an ``invalid-mode`` error and is
    returned verbatim so callers never guess.
    """
    raw = config.get("mode") if isinstance(config, dict) else None
    if raw is None:
        return "in-house", [
            finding(
                "missing-mode",
                'Config has no "mode"; assuming in-house. Add "mode" to .mos/config.yaml.',
                severity="warning",
                path=".mos/config.yaml",
            )
        ]
    if raw not in MODES:
        return str(raw), [
            finding(
                "invalid-mode",
                f"Config mode {raw!r} is not one of in-house, agency, client.",
                path=".mos/config.yaml",
            )
        ]
    return raw, []


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "business"
