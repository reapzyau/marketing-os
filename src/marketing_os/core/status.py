from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_os.core.results import envelope, finding, next_action
from marketing_os.core.schema import load_schema, read_config
from marketing_os.core.skills import bundled_skills, inspect_runtimes
from marketing_os.core.validation import validation_findings


def _substantive(path: Path) -> bool:
    if not path.is_file():
        return False
    useful: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.lower().startswith("todo:"):
            continue
        useful.append(line)
    return len(" ".join(useful)) >= 30


def _offer_files(root: Path) -> list[Path]:
    base = root / "business" / "offers"
    if not base.is_dir():
        return []
    return sorted(
        path
        for path in base.glob("*/offer.md")
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", path.parent.name)
    )


def context_status(root: Path) -> dict[str, Any]:
    schema = load_schema()
    fields = {
        name: {"path": relative, "complete": _substantive(root / relative)}
        for name, relative in schema["context_files"].items()
    }
    offers = _offer_files(root)
    fields["offer"] = {
        "path": "business/offers/<offer-slug>/offer.md",
        "complete": any(_substantive(path) for path in offers),
        "files": [path.relative_to(root).as_posix() for path in offers],
    }
    required = ("brand", "voice", "audience", "offer")
    missing = [name for name in required if not fields[name]["complete"]]
    return {"ready": not missing, "required": list(required), "missing": missing, "fields": fields}


def status_repo(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    config = read_config(root)
    if config is None:
        return envelope(
            "status",
            root,
            ok=False,
            findings=[
                finding("not-marketing-os", "This is not a marketing-os business repository.")
            ],
            action=next_action("run-setup", "Create a new business brain with the setup skill."),
            repo_state="absent",
            business={},
            context={"ready": False, "missing": ["brand", "voice", "audience", "offer"]},
            runtimes=inspect_runtimes(root),
            installed_skills=list(bundled_skills()),
        )

    findings = validation_findings(root)
    errors = [item for item in findings if item["severity"] == "error"]
    context = context_status(root)
    runtimes = inspect_runtimes(root)
    runtime_ready = all(item["ready"] for item in runtimes.values())

    if errors:
        state = "invalid"
        action = next_action(
            "repair-structure", "Repair structural errors before doing business work."
        )
    elif not runtime_ready:
        state = "needs-runtime-sync"
        action = next_action("sync-skills", "Synchronize the shared skills for both runtimes.")
    elif not context["ready"]:
        state = "needs-context"
        first = context["missing"][0]
        action = next_action(f"complete-{first}", f"Complete the {first} context first.")
    else:
        state = "ready"
        action = next_action(
            "follow-current-focus", "Use CONTEXT.md to continue the current priority."
        )

    return envelope(
        "status",
        root,
        ok=not errors,
        findings=findings,
        action=action,
        repo_state=state,
        schema_version=config.get("schema_version"),
        business={"name": config.get("business_name", "")},
        context=context,
        runtimes=runtimes,
        installed_skills=list(bundled_skills()),
    )


def doctor_repo(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    status = status_repo(root)
    runtimes = status.get("runtimes", {})
    runtime_ready = bool(runtimes) and all(item.get("ready", False) for item in runtimes.values())
    structural_errors = [item for item in status["findings"] if item.get("severity") == "error"]
    findings = list(status["findings"])
    if not runtime_ready:
        findings.append(
            finding(
                "runtime-not-ready", "Claude Code and Codex skill discovery are not both ready."
            )
        )
    ok = not structural_errors and runtime_ready
    return envelope(
        "doctor",
        root,
        ok=ok,
        findings=findings,
        action=next_action(
            "run-start" if ok else "repair-health",
            "The repository is healthy; continue with the start skill."
            if ok
            else "Repair structure or synchronize skills, then run doctor again.",
        ),
        checks={
            "structure": not structural_errors,
            "runtime_wiring": runtime_ready,
            "context_ready": status.get("context", {}).get("ready", False),
        },
        runtimes=runtimes,
    )
