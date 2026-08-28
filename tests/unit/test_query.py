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


def _catalogued(root: Path) -> None:
    from marketing_os.core.catalog import build_repo

    build_repo(root)


def test_query_widens_beyond_business_and_wiki(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    _write(
        root / "outputs" / "2026" / "08" / "2026-08-20-launch" / "recap.md",
        "# Launch recap\n\nThe launch recap covers the launch results.\n",
    )
    result = query_repo(root, "launch recap")
    paths = [item["path"] for item in result["candidates"]]
    assert "outputs/2026/08/2026-08-20-launch/recap.md" in paths


def test_query_ignores_archived_material(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    _write(root / "archive" / "old-pricing.md", "# Old\n\npricing pricing pricing pricing\n")
    result = query_repo(root, "pricing")
    assert all(not item["path"].startswith("archive/") for item in result["candidates"])


def test_query_prefers_the_catalog_when_one_exists(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    assert query_repo(root, "pricing")["source"] == "body-scan"
    _catalogued(root)
    result = query_repo(root, "pricing strategy")
    assert result["source"] == "catalog"
    assert result["candidates"][0]["path"] == "business/strategy/pricing.md"


def test_query_falls_back_when_the_catalog_has_no_answer(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    # The term appears only deep in the body, so no catalogued field carries it.
    _write(
        root / "business" / "brand" / "deep.md",
        "---\ntitle: Brand notes\ndescription: General notes on the brand.\n---\n\n"
        "# Brand notes\n\nGeneral notes on the brand.\n\nA buried heliotrope reference.\n",
    )
    _catalogued(root)
    result = query_repo(root, "heliotrope")
    assert result["source"] == "body-scan"
    assert [item["path"] for item in result["candidates"]] == ["business/brand/deep.md"]


def test_query_returns_the_navigation_route(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    _write(root / "_index.md", "# Root\n")
    _write(root / "business" / "_index.md", "# Business\n")
    result = query_repo(root, "pricing strategy")
    assert result["route"] == ["_index.md", "business/_index.md"]


def test_query_route_is_empty_without_generated_indexes(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    assert query_repo(root, "pricing")["route"] == []


def test_grep_finds_literal_strings(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    _write(root / "business" / "brand" / "links.md", "# Links\n\nSee https://example.com/a?b=1\n")
    result = query_repo(root, "https://example.com/a?b=1", literal=True)
    assert result["mode"] == "grep"
    assert result["matches"][0]["path"] == "business/brand/links.md"
    assert result["matches"][0]["line"] == 3


def test_grep_reports_no_matches_without_failing(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _make_repo(root)
    result = query_repo(root, "no-such-literal-string", literal=True)
    assert result["ok"] is True
    assert result["matches"] == []
    assert any(item["code"] == "no-matches" for item in result["findings"])


def test_score_catalog_weights_title_above_body_context(tmp_path: Path) -> None:
    from marketing_os.core.catalog import build_catalog
    from marketing_os.core.query import score_catalog

    root = tmp_path / "brain"
    _make_repo(root)
    scored = score_catalog(build_catalog(root), ["pricing"])
    ranked = {relative: score for relative, score, _matched in scored}
    assert ranked["business/strategy/pricing.md"] > ranked["business/audience/primary.md"]
    assert not any(path.endswith("_index.md") for path in ranked)
