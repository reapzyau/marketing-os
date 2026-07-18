from pathlib import Path

from marketing_os.core.query import query_repo, score_corpus, tokenize
from marketing_os.core.schema import config_text


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_repo(root: Path) -> None:
    _write(root / ".mos" / "config.yaml", config_text("Example Business"))
    _write(root / "BRAIN.md", "# Brain\n\nOperating context for the business.\n")
    _write(root / "CONTEXT.md", "# Context\n\nCurrent focus is the pricing review.\n")
    _write(
        root / "business" / "strategy" / "pricing.md",
        "# Pricing\n\nPricing strategy and pricing tiers for the pricing model.\n",
    )
    _write(
        root / "business" / "audience" / "primary.md",
        "# Audience\n\nSmall teams evaluating pricing options.\n",
    )
    _write(root / "knowledge" / "wiki" / "_index.md", "# Index\n\n- pricing\n")
    _write(root / "knowledge" / "wiki" / "_log.md", "# Log\n")
    _write(
        root / "knowledge" / "wiki" / "channels.md",
        "# Channels\n\nDistribution channels overview.\n",
    )


def test_tokenize_keeps_long_alphanumeric_terms() -> None:
    assert tokenize("Pricing, a B2B GROWTH plan!") == ["pricing", "b2b", "growth", "plan"]


def test_query_returns_scored_candidates(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    result = query_repo(root, "pricing strategy")

    assert result["schema"] == "mos.query.v1"
    assert result["ok"] is True
    assert result["question"] == "pricing strategy"
    paths = [item["path"] for item in result["candidates"]]
    assert "business/strategy/pricing.md" in paths
    top = result["candidates"][0]
    assert top["path"] == "business/strategy/pricing.md"
    assert "pricing" in top["matched_terms"]
    assert top["score"] >= 4
    assert result["indexes"] == ["knowledge/wiki/_index.md"]


def test_underscore_wiki_files_are_excluded(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    result = query_repo(root, "index log")
    paths = [item["path"] for item in result["candidates"]]
    assert "knowledge/wiki/_index.md" not in paths
    assert "knowledge/wiki/_log.md" not in paths


def test_query_zero_matches_warns_but_stays_ok(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    result = query_repo(root, "zzzqqq nonexistentterm")
    assert result["ok"] is True
    assert result["candidates"] == []
    codes = {(item["code"], item["severity"]) for item in result["findings"]}
    assert ("no-matches", "warning") in codes
    assert result["next_action"]["id"] == "synthesize-answer"


def test_query_limit_caps_candidates(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    result = query_repo(root, "pricing", limit=1)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["path"] == "business/strategy/pricing.md"


def test_query_is_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    first = query_repo(root, "pricing strategy audience")
    second = query_repo(root, "pricing strategy audience")
    assert first["candidates"] == second["candidates"]


def test_score_corpus_tie_break_by_path(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _write(root / ".mos" / "config.yaml", config_text("Example Business"))
    _write(root / "business" / "brand" / "alpha.md", "# Alpha\n\nsignal here.\n")
    _write(root / "business" / "brand" / "beta.md", "# Beta\n\nsignal here.\n")
    scored = score_corpus(root, ["signal"])
    ordered = [path.relative_to(root.resolve()).as_posix() for path, _score, _matched in scored]
    assert ordered == ["business/brand/alpha.md", "business/brand/beta.md"]
    assert all(score == 1 for _path, score, _matched in scored)


def test_score_corpus_empty_terms_returns_nothing(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    assert score_corpus(root, []) == []
