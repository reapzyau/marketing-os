import json
from pathlib import Path

from marketing_os.core.schema import assets_root, load_schema
from marketing_os.core.setup import setup_repo
from marketing_os.core.skills import bundled_skills


def test_package_has_one_three_skill_catalog() -> None:
    assert bundled_skills() == ("mos-setup", "mos-start", "mos-help")
    assert not Path(".claude/skills").exists()
    assert not Path(".agents/skills").exists()


def test_schema_is_machine_readable_and_versioned() -> None:
    schema = load_schema()
    assert schema["schema"] == "mos.business-repo.v1"
    assert schema["version"] == 1
    assert "business/brand/voice.md" in schema["required_files"]
    json.loads((assets_root() / "schema.json").read_text(encoding="utf-8"))


def test_skills_document_only_shipped_commands() -> None:
    skills = assets_root() / "skills"
    text = "\n".join(path.read_text(encoding="utf-8") for path in skills.rglob("SKILL.md"))
    for command in ("mos setup", "mos status", "mos validate", "mos doctor", "mos skills sync"):
        assert command in text


def test_setup_matches_golden_tree(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Golden Business", "all", apply=True)
    actual = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    expected = sorted(
        line
        for line in (Path(__file__).parents[1] / "fixtures" / "golden-tree.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    )
    assert actual == expected
