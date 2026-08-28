"""Catalogue every markdown document in a brain.

The catalogue is the retrieval interface. Corpus2Skill (arXiv 2604.14572) and
"Is Grep All You Need?" (arXiv 2605.15184) both land on the same result: for a corpus an
agent navigates with a filesystem, a hierarchy of small index files beats an embedding
index. Both need one thing first — every document must state what it is. This module
reads that statement, and nothing here calls a model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from marketing_os.core.results import envelope, finding, next_action
from marketing_os.core.schema import load_schema

SKIP_DIRS = frozenset(
    {
        ".git",
        ".mos",
        ".claude",
        ".agents",
        ".codex",
        ".obsidian",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
    }
)

WIKILINK = re.compile(r"\[\[([^\]|#]+)")
RELATED_HEADING = re.compile(r"(?m)^##\s+Related\s*$")
KEY_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$")
SEQUENCE_ITEM = re.compile(r"^\s+-\s+(.*)$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a YAML-fenced frontmatter block from its body.

    Understands the subset the contract uses: scalars, inline ``[a, b]`` lists, and block
    sequences. Anything richer is not worth a dependency here.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict[str, Any] = {}
    key: str | None = None
    body_at: int | None = None
    for offset, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_at = offset + 1
            break
        item = SEQUENCE_ITEM.match(line)
        if item and key is not None:
            value = _unquote(item.group(1))
            existing = meta.get(key)
            if isinstance(existing, list):
                existing.append(value)
            else:
                meta[key] = [value] if not existing else [existing, value]
            continue
        match = KEY_LINE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        raw = match.group(2).strip()
        if raw.startswith("[") and raw.endswith("]"):
            meta[key] = [_unquote(part) for part in raw[1:-1].split(",") if part.strip()]
        elif raw:
            meta[key] = _unquote(raw)
        else:
            meta[key] = ""
    if body_at is None:
        return {}, text
    return meta, "\n".join(lines[body_at:])


def first_sentence(body: str, limit: int = 160) -> str:
    """Best available one-line summary when a document declares no description."""
    for para in body.split("\n\n"):
        text = para.strip()
        if not text or text.startswith(("#", "|", ">", "```", "- ", "* ", "!")):
            continue
        text = re.sub(r"\[\[([^\]|]+)\|?([^\]]*)\]\]", r"\2\1", text)
        text = re.sub(r"[*_`#]", "", text).replace("\n", " ").strip()
        if len(text) < 20:
            continue
        if len(text) <= limit:
            return text
        return text[:limit].rsplit(" ", 1)[0] + "..."
    return ""


def excluded_roots() -> tuple[str, ...]:
    return tuple(load_schema().get("excluded_from_grounding", ()))


def docs_iter(root: Path) -> list[tuple[Path, str]]:
    """Every catalogued markdown file, as ``(absolute path, repo-relative posix path)``."""
    skipped = excluded_roots()
    found: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        parts = relative.parts
        if any(part in SKIP_DIRS for part in parts):
            continue
        if parts and parts[0] in skipped:
            continue
        found.append((path, relative.as_posix()))
    return found


def _link_targets(meta: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    for key in ("related", "sources"):
        value = meta.get(key)
        if isinstance(value, list):
            targets.extend(str(item) for item in value)
        elif isinstance(value, str) and value:
            targets.append(value)
    return [item.strip() for item in targets if "/" in item or item.endswith(".md")]


def describe(path: Path, relative: str, text: str) -> dict[str, Any]:
    meta, body = parse_frontmatter(text)
    contract = load_schema()["frontmatter_contract"]
    links = {match.strip() for match in WIKILINK.findall(text)}
    links.update(target.strip() for target in _link_targets(meta))
    description = str(meta.get("description") or "").strip() or first_sentence(body)
    present = [key for key in contract["connective_keys"] if meta.get(key)]
    return {
        "title": str(meta.get("title") or path.stem.replace("-", " ")).strip(),
        "description": description,
        "type": str(meta.get("type") or ""),
        "status": str(meta.get("status") or ""),
        "date": str(meta.get("date") or ""),
        "words": len(body.split()),
        "links_out": sorted(links),
        "connective_keys": present,
        "has_frontmatter": bool(meta),
        "has_related_block": bool(RELATED_HEADING.search(text)),
        "missing_keys": [key for key in contract["required_keys"] if not meta.get(key)],
        "path": relative,
    }


def build_catalog(root: Path) -> dict[str, dict[str, Any]]:
    """Read every document once and return the catalogue, without writing anything."""
    docs: dict[str, dict[str, Any]] = {}
    for path, relative in docs_iter(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        docs[relative] = describe(path, relative, text)
    return docs


def catalog_path(root: Path) -> Path:
    return root / ".mos" / "local" / "catalog.json"


def write_catalog(root: Path, docs: dict[str, dict[str, Any]]) -> Path:
    target = catalog_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(docs, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def load_catalog(root: Path) -> dict[str, dict[str, Any]] | None:
    """Return the persisted catalogue, or ``None`` when it is absent or unreadable."""
    target = catalog_path(root)
    if not target.is_file():
        return None
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


NAV_NAMES = frozenset({"_index.md", "_log.md"})


def coverage(docs: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Contract coverage over real documents.

    Generated indexes are excluded: they are the map, not the territory, and counting
    them would flatter every percentage the sensors report.
    """
    real = [item for path, item in docs.items() if Path(path).name not in NAV_NAMES]
    return {
        "documents": len(real),
        "with_frontmatter": sum(1 for item in real if item["has_frontmatter"]),
        "with_description": sum(1 for item in real if item["description"]),
        "with_outgoing_links": sum(
            1 for item in real if item["links_out"] or item["has_related_block"]
        ),
    }


def build_repo(root: Path) -> dict[str, Any]:
    """``mos index build`` — catalogue the brain into machine-local state."""
    root = root.expanduser().resolve()
    docs = build_catalog(root)
    target = write_catalog(root, docs)
    stats = coverage(docs)
    findings: list[dict[str, str]] = []
    if not docs:
        findings.append(
            finding("empty-corpus", "No markdown documents to catalogue.", severity="warning")
        )
    return envelope(
        "index-build",
        root,
        ok=True,
        changes=[f"write {target.relative_to(root).as_posix()}"],
        findings=findings,
        action=next_action(
            "sync-indexes", "Regenerate the navigation hierarchy with `mos index sync . --yes`."
        ),
        catalog=target.relative_to(root).as_posix(),
        coverage=stats,
    )
