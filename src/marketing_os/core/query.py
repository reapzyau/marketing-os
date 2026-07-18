from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from marketing_os.core.results import envelope, finding, next_action

TERM = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric terms longer than two characters."""
    return [term for term in TERM.findall(text.lower()) if len(term) > 2]


def _corpus_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for name in ("BRAIN.md", "CONTEXT.md"):
        candidate = root / name
        if candidate.is_file():
            files.append(candidate)
    for base in (root / "business", root / "knowledge" / "wiki"):
        if base.is_dir():
            files.extend(
                path
                for path in base.rglob("*.md")
                if path.is_file() and not path.name.startswith("_")
            )
    unique = {path.resolve(): path for path in files}
    return sorted(unique.values(), key=lambda path: path.as_posix())


def score_corpus(root: Path, terms: list[str]) -> list[tuple[Path, int, list[str]]]:
    """Score every corpus document against the query terms.

    Returns ``(path, score, matched_terms)`` tuples for documents with a
    positive score, sorted by descending score with a deterministic path
    tie-break. Score is the summed term frequency across the filename stem and
    body; ``matched_terms`` are the sorted unique query terms that appeared.
    """
    root = root.expanduser().resolve()
    wanted = [term for term in terms if term]
    results: list[tuple[Path, int, list[str]]] = []
    if not wanted:
        return results
    for path in _corpus_files(root):
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        counts = Counter(tokenize(path.stem + " " + body))
        score = sum(counts[term] for term in wanted)
        if score <= 0:
            continue
        matched = sorted({term for term in wanted if counts[term] > 0})
        results.append((path, score, matched))
    results.sort(key=lambda item: (-item[1], item[0].as_posix()))
    return results


def query_repo(root: Path, question: str, *, limit: int = 5) -> dict[str, Any]:
    """Plan deterministic retrieval for a question against the repository corpus."""
    root = root.expanduser().resolve()
    terms = tokenize(question)
    scored = score_corpus(root, terms)
    top = scored[: limit if limit > 0 else 0]
    candidates = [
        {
            "path": path.relative_to(root).as_posix(),
            "score": score,
            "matched_terms": matched,
        }
        for path, score, matched in top
    ]
    index_path = root / "knowledge" / "wiki" / "_index.md"
    indexes = [index_path.relative_to(root).as_posix()] if index_path.is_file() else []

    findings: list[dict[str, str]] = []
    if not candidates:
        findings.append(
            finding(
                "no-matches",
                "No corpus document matched the question terms.",
                severity="warning",
            )
        )
    action = next_action(
        "synthesize-answer",
        "Read the candidate files and answer the question with citations to those "
        "paths; if the candidates are thin, browse knowledge/wiki/_index.md.",
    )
    return envelope(
        "query",
        root,
        ok=True,
        findings=findings,
        action=action,
        question=question,
        candidates=candidates,
        indexes=indexes,
    )
