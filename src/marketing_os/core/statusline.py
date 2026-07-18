from __future__ import annotations

from pathlib import Path
from typing import Any

from marketing_os.core.results import envelope
from marketing_os.core.schema import find_root, read_config, repo_mode
from marketing_os.core.skills import bundled_skills, inspect_runtimes

SEPARATOR = " | "


def statusline_repo(start: Path) -> dict[str, Any]:
    start = start.expanduser().resolve()
    root = find_root(start)
    if root is None:
        return envelope("statusline", start, ok=True, active=False, line="")

    config = read_config(root) or {}
    business_name = str(config.get("business_name", "")).strip()
    # Resolve mode through the shared read semantics. Render the segment only for
    # an explicit, valid mode; legacy/missing config omits it (fact null), and an
    # invalid value keeps the verbatim string as a fact but stays off the line.
    resolved, mode_findings = repo_mode(config)
    codes = {item["code"] for item in mode_findings}
    if "missing-mode" in codes:
        mode = None
        show_mode = False
    elif "invalid-mode" in codes:
        mode = resolved
        show_mode = False
    else:
        mode = resolved
        show_mode = True

    total = len(bundled_skills())
    runtime = inspect_runtimes(root).get("claude", {})
    missing = runtime.get("missing", [])
    mismatched = runtime.get("mismatched", [])
    # A missing OR a stale (mismatched) skill is not installed.
    uninstalled = (len(missing) if isinstance(missing, list) else 0) + (
        len(mismatched) if isinstance(mismatched, list) else 0
    )
    installed = total - uninstalled

    # Legacy/missing or invalid modes omit the mode segment.
    segments = ["mos", business_name]
    if show_mode:
        segments.append(mode)
    segments.append(f"skills {installed}/{total}")
    line = SEPARATOR.join(segments)

    return envelope(
        "statusline",
        root,
        ok=True,
        active=True,
        line=line,
        business={"name": business_name},
        skills={"installed": installed, "total": total},
        mode=mode,
    )
