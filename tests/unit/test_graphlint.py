from pathlib import Path

from marketing_os.core.graphlint import contract_findings, expected_type
from marketing_os.core.schema import config_text
from marketing_os.core.validation import validate_repo

TODAY = "2026-08-20"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _codes(root: Path, relative: str) -> set[str]:
    return {item["code"] for item in contract_findings(root) if item["path"] == relative}


def _brain(root: Path) -> None:
    _write(root / ".mos" / "config.yaml", config_text("Example Business"))


def test_expected_type_prefers_the_longest_folder_match() -> None:
    folders = {"business": "business", "business/decisions": "decision"}
    assert expected_type("business/brand/brand.md", folders) == "business"
    assert expected_type("business/decisions/2026/08/x/decision.md", folders) == "decision"
    assert expected_type("nowhere/x.md", folders) is None


def test_missing_frontmatter_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(root / "business" / "notes.md", "# Notes\n\nNo contract block here.\n")
    assert "missing-frontmatter" in _codes(root, "business/notes.md")


def test_partial_frontmatter_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(
        root / "business" / "notes.md",
        "---\ntitle: Notes\ntype: business\nrelated:\n  - business/brand/brand.md\n---\n\nBody.\n",
    )
    findings = [item for item in contract_findings(root) if item["path"] == "business/notes.md"]
    assert any("description" in item["message"] for item in findings)


def test_a_deliverable_without_sources_is_unfinished(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(
        root / "content" / "2026" / "08" / "2026-08-20-launch" / "post.md",
        f"---\ntitle: Launch post\ntype: content\ndescription: The launch announcement.\n"
        f"date: {TODAY}\nstatus: active\nrelated:\n  - business/brand/voice.md\n---\n\nBody.\n",
    )
    codes = _codes(root, "content/2026/08/2026-08-20-launch/post.md")
    assert "output-without-sources" in codes


def test_sources_satisfy_a_deliverable(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(
        root / "outputs" / "2026" / "08" / "2026-08-20-brief" / "brief.md",
        f"---\ntitle: Brief\ntype: output\ndescription: A working brief.\n"
        f"date: {TODAY}\nstatus: active\nsources:\n  - knowledge/wiki/research.md\n---\n\nBody.\n",
    )
    codes = _codes(root, "outputs/2026/08/2026-08-20-brief/brief.md")
    assert "output-without-sources" not in codes
    assert "missing-connective-key" not in codes


def test_missing_connective_key_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(
        root / "business" / "notes.md",
        f"---\ntitle: Notes\ntype: business\ndescription: Some notes.\n"
        f"date: {TODAY}\nstatus: active\n---\n\nBody.\n",
    )
    assert "missing-connective-key" in _codes(root, "business/notes.md")


def test_type_must_match_the_vocabulary_and_the_folder(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(
        root / "business" / "wrong-word.md",
        f"---\ntitle: A\ntype: nonsense\ndescription: A doc.\ndate: {TODAY}\n"
        f"status: active\nrelated:\n  - business/brand/brand.md\n---\n\nBody.\n",
    )
    _write(
        root / "business" / "wrong-place.md",
        f"---\ntitle: B\ntype: campaign\ndescription: A doc.\ndate: {TODAY}\n"
        f"status: active\nrelated:\n  - business/brand/brand.md\n---\n\nBody.\n",
    )
    assert "invalid-type" in _codes(root, "business/wrong-word.md")
    assert "invalid-type" in _codes(root, "business/wrong-place.md")


def test_invalid_status_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(
        root / "business" / "notes.md",
        f"---\ntitle: Notes\ntype: business\ndescription: Some notes.\ndate: {TODAY}\n"
        f"status: wip\nrelated:\n  - business/brand/brand.md\n---\n\nBody.\n",
    )
    assert "invalid-status" in _codes(root, "business/notes.md")


def test_structural_files_are_exempt(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    for name in ("BRAIN.md", "CONTEXT.md", "README.md", "AGENTS.md", "CLAUDE.md", "CONTRACT.md"):
        _write(root / name, "# Structural\n\nNo contract block.\n")
    _write(root / "knowledge" / "wiki" / "_index.md", "# Index\n")
    assert contract_findings(root) == []


def test_excalidraw_drawings_are_exempt_by_suffix(tmp_path: Path) -> None:
    """A drawing's body is Excalidraw's data, not a document; the contract skips it."""
    root = tmp_path / "brain"
    _brain(root)
    relative = "knowledge/sources/2026/08/2026-08-20-funnel"
    folder = root / relative
    _write(
        folder / "funnel.excalidraw.md",
        "---\nexcalidraw-plugin: parsed\n---\n# Drawing\n" + "word " * 300,
    )
    assert _codes(root, f"{relative}/funnel.excalidraw.md") == set()
    # A plain note beside it still has to carry the contract block.
    _write(folder / "notes.md", "# Notes\n")
    assert "missing-frontmatter" in _codes(root, f"{relative}/notes.md")


def test_substantial_dead_ends_are_reported(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(
        root / "business" / "long.md",
        f"---\ntitle: Long\ntype: business\ndescription: A long document.\ndate: {TODAY}\n"
        f"status: active\nproduced_by: test\n---\n\n" + "word " * 200,
    )
    assert "unlinked-document" in _codes(root, "business/long.md")


def test_validate_keeps_gaps_as_warnings_until_strict(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _brain(root)
    _write(root / "business" / "notes.md", "# Notes\n\nNo contract block here.\n")
    relaxed = validate_repo(root)
    strict = validate_repo(root, strict=True)
    gaps = relaxed["summary"]["contract_gaps"]
    assert gaps > 0
    assert all(
        item["severity"] == "warning"
        for item in relaxed["findings"]
        if item["code"] == "missing-frontmatter"
    )
    assert strict["ok"] is False
    assert strict["strict"] is True
    assert any(
        item["severity"] == "error"
        for item in strict["findings"]
        if item["code"] == "missing-frontmatter"
    )
