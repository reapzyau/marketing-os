from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_os.core.results import envelope, finding, next_action
from marketing_os.core.schema import load_schema, read_config

YEAR = re.compile(r"^\d{4}$")
MONTH = re.compile(r"^(0[1-9]|1[0-2])$")
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
QUARTER = re.compile(r"^Q[1-4]$")
YEAR_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _visible_children(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return [child for child in path.iterdir() if child.name != ".gitkeep"]


def _check_year_month_dated(root: Path, relative: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    base = root / relative
    for year in _visible_children(base):
        if not year.is_dir() or not YEAR.fullmatch(year.name):
            findings.append(finding("invalid-year", "Expected a YYYY directory.", path=str(year)))
            continue
        for month in _visible_children(year):
            if not month.is_dir() or not MONTH.fullmatch(month.name):
                findings.append(
                    finding("invalid-month", "Expected an MM directory.", path=str(month))
                )
                continue
            for artifact in _visible_children(month):
                if not artifact.is_dir() or not DATED.fullmatch(artifact.name):
                    findings.append(
                        finding(
                            "invalid-dated-artifact",
                            "Expected a YYYY-MM-DD-slug directory.",
                            path=str(artifact),
                        )
                    )
    return findings


def _check_reporting(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for year in _visible_children(root / "reporting"):
        if not year.is_dir() or not YEAR.fullmatch(year.name):
            findings.append(finding("invalid-year", "Expected a YYYY directory.", path=str(year)))
            continue
        for quarter in _visible_children(year):
            if not quarter.is_dir() or not QUARTER.fullmatch(quarter.name):
                findings.append(
                    finding("invalid-quarter", "Expected a Q1-Q4 directory.", path=str(quarter))
                )
                continue
            for month in _visible_children(quarter):
                if not month.is_dir() or not YEAR_MONTH.fullmatch(month.name):
                    findings.append(
                        finding(
                            "invalid-report-month", "Expected a YYYY-MM directory.", path=str(month)
                        )
                    )
    return findings


def validation_findings(root: Path) -> list[dict[str, str]]:
    schema = load_schema()
    findings: list[dict[str, str]] = []
    config = read_config(root)
    if config is None:
        findings.append(
            finding(
                "missing-or-invalid-config",
                "Missing or invalid .mos/config.yaml.",
                path=".mos/config.yaml",
            )
        )
    elif (
        config.get("schema") != schema["schema"]
        or config.get("schema_version") != schema["version"]
    ):
        findings.append(
            finding(
                "unsupported-schema",
                "The repository schema is not supported.",
                path=".mos/config.yaml",
            )
        )

    for relative in schema["required_directories"]:
        if not (root / relative).is_dir():
            findings.append(
                finding("missing-directory", "Required directory is missing.", path=relative)
            )
    for relative in schema["required_files"]:
        if not (root / relative).is_file():
            findings.append(finding("missing-file", "Required file is missing.", path=relative))

    allowed = set(schema["allowed_top_level"])
    allowed_files = {
        Path(relative).name for relative in schema["required_files"] if "/" not in relative
    }
    if root.is_dir():
        for child in root.iterdir():
            if child.name.startswith(".") or child.name in allowed or child.name in allowed_files:
                continue
            findings.append(
                finding(
                    "unknown-top-level",
                    "Top-level path is outside the canonical architecture.",
                    severity="warning",
                    path=child.name,
                )
            )

    for relative in (
        "content",
        "campaigns",
        "outputs",
        "business/decisions",
        "knowledge/sources",
    ):
        findings.extend(_check_year_month_dated(root, relative))
    findings.extend(_check_reporting(root))
    return findings


def validate_repo(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    findings = validation_findings(root)
    errors = [item for item in findings if item["severity"] == "error"]
    return envelope(
        "validate",
        root,
        ok=not errors,
        findings=findings,
        action=next_action(
            "repair-structure" if errors else "run-status",
            "Repair the reported structural errors."
            if errors
            else "Inspect context readiness and the next useful action.",
        ),
        summary={
            "errors": len(errors),
            "warnings": sum(1 for item in findings if item["severity"] == "warning"),
        },
    )
