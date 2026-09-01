from __future__ import annotations

import json
from pathlib import Path

from marketing_os.core.attach import (
    apply_attach,
    legacy_summary,
    parse_simple_yaml,
    plan_attach,
)
from marketing_os.core.schema import read_config
from marketing_os.core.setup import setup_repo

LEGACY_YAML = "mode: in-house\nname: the-vibe-marketing-lab\nrepo: tvml\ncreated: '2026-06-17'\n"
BRAIN = "# My brain\n\nOperator-written, never to be touched.\n"
BRAND = "# Brand\n\nReal brand content.\n"


def _legacy_tree(root: Path, config: str | None = LEGACY_YAML) -> Path:
    (root / ".mos").mkdir(parents=True)
    if config is not None:
        (root / ".mos" / "config.yaml").write_text(config, encoding="utf-8")
    (root / "BRAIN.md").write_text(BRAIN, encoding="utf-8")
    (root / "business" / "brand").mkdir(parents=True)
    (root / "business" / "brand" / "brand.md").write_text(BRAND, encoding="utf-8")
    (root / "notes").mkdir()
    return root


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        item.relative_to(root).as_posix(): item.read_bytes()
        for item in root.rglob("*")
        if item.is_file()
    }


def test_parse_simple_yaml_reads_flat_pairs_only() -> None:
    parsed = parse_simple_yaml(
        "---\n# comment\nmode: agency\nname: 'Quoted Co'\nnested:\n  child: x\n"
        'business_name: "Real Name"  # trailing\n- item\n'
    )
    assert parsed == {"mode": "agency", "name": "Quoted Co", "business_name": "Real Name"}


def test_plan_is_non_mutating_and_lists_config_rewrite(tmp_path: Path) -> None:
    root = _legacy_tree(tmp_path / "legacy")
    before = _snapshot(root)
    result = plan_attach(root)
    assert result["ok"] is True
    assert result["planned"] is True
    assert result["applied"] is False
    assert result["schema"] == "mos.attach.v1"
    assert result["name"] == "the-vibe-marketing-lab"
    assert result["mode"] == "in-house"
    assert result["legacy"]["repo"] == "tvml"
    assert "backup .mos/config.legacy.yaml" in result["changes"]
    assert "config .mos/config.yaml" in result["changes"]
    assert "create CONTRACT.md" in result["changes"]
    assert "create BRAIN.md" not in result["changes"]
    # Every directory apply makes gets a .gitkeep, so the plan names both.
    assert "mkdir archive" in result["changes"]
    assert "create archive/.gitkeep" in result["changes"]
    assert not any(change.endswith("business/brand/brand.md") for change in result["changes"])
    assert result["unrouted"] == ["notes"]
    assert result["next_action"]["id"] == "apply-attach"
    assert _snapshot(root) == before


def test_apply_writes_json_config_backup_and_only_missing_files(tmp_path: Path) -> None:
    root = _legacy_tree(tmp_path / "legacy")
    before = _snapshot(root)
    result = apply_attach(root)
    assert result["ok"] is True
    assert result["applied"] is True
    assert result["next_action"]["id"] == "run-status"
    assert str(root) in result["next_action"]["reason"]

    config = read_config(root)
    assert config == {
        "schema": "mos.business-repo.v1",
        "schema_version": 1,
        "business_name": "the-vibe-marketing-lab",
        "mode": "in-house",
    }
    assert (root / ".mos" / "config.legacy.yaml").read_text(encoding="utf-8") == LEGACY_YAML
    assert (root / "CONTRACT.md").is_file()
    assert (root / "AGENTS.md").is_file()
    assert (root / ".gitattributes").is_file()
    assert (root / "archive").is_dir()
    assert (root / ".claude" / "skills" / "mos-start" / "SKILL.md").is_file()
    assert (root / ".agents" / "skills" / "mos-start" / "SKILL.md").is_file()
    # No operator content is ever created by attach.
    assert not (root / "business" / "brand" / "voice.md").exists()
    assert not (root / "knowledge" / "wiki" / "_index.md").exists()

    after = _snapshot(root)
    for relative, data in before.items():
        if relative == ".mos/config.yaml":
            continue
        assert after[relative] == data, relative
    codes = {item["code"] for item in result["findings"]}
    assert "missing-content-file" in codes
    assert "off-schema-entry" in codes


def test_apply_is_idempotent_and_second_run_is_a_noop(tmp_path: Path) -> None:
    root = _legacy_tree(tmp_path / "legacy")
    apply_attach(root)
    snapshot = _snapshot(root)
    again = apply_attach(root)
    assert again["ok"] is True
    assert again["changes"] == []
    assert again["findings"][0]["code"] == "already-attached"
    assert again["name"] == "the-vibe-marketing-lab"
    assert _snapshot(root) == snapshot


def test_the_plan_names_every_file_apply_writes(tmp_path: Path) -> None:
    root = _legacy_tree(tmp_path / "legacy")
    before = _snapshot(root)
    planned = plan_attach(root)["changes"]
    apply_attach(root)
    written = sorted(set(_snapshot(root)) - set(before))
    named = {
        change.split(" ", 1)[1]
        for change in planned
        if change.split(" ", 1)[0] in ("backup", "config", "create")
    }
    # Runtime skill copies and their manifest are named by the skills planner in its own
    # words; every scaffold file, keep-file and config write is named by attach itself.
    skills = (".claude/", ".agents/", ".mos/local/")
    scaffold = [path for path in written if not path.startswith(skills)]
    assert scaffold, "the legacy tree gained scaffold files"
    assert set(scaffold) <= named, sorted(set(scaffold) - named)


def test_a_second_different_config_gets_a_numbered_backup(tmp_path: Path) -> None:
    """The first attach keeps the legacy text as config.legacy.yaml. Restore a different
    legacy config and attach again: the new text must be kept too, under the next number,
    never dropped because a backup already exists, never written over the first one."""
    root = _legacy_tree(tmp_path / "legacy")
    apply_attach(root)
    restored = "mode: agency\nname: restored-name\n"
    (root / ".mos" / "config.yaml").write_text(restored, encoding="utf-8")

    planned = plan_attach(root)
    assert "backup .mos/config.legacy.1.yaml" in planned["changes"]
    assert "backup .mos/config.legacy.yaml" not in planned["changes"]
    result = apply_attach(root)

    assert result["ok"] is True and result["name"] == "restored-name"
    assert result["mode"] == "agency"
    assert (root / ".mos" / "config.legacy.yaml").read_text(encoding="utf-8") == LEGACY_YAML
    assert (root / ".mos" / "config.legacy.1.yaml").read_text(encoding="utf-8") == restored
    assert read_config(root)["business_name"] == "restored-name"

    # A third, again different: the next free number.
    third = "mode: in-house\nname: third-name\n"
    (root / ".mos" / "config.yaml").write_text(third, encoding="utf-8")
    apply_attach(root)
    assert (root / ".mos" / "config.legacy.2.yaml").read_text(encoding="utf-8") == third
    assert (root / ".mos" / "config.legacy.1.yaml").read_text(encoding="utf-8") == restored


def test_a_config_already_backed_up_is_not_backed_up_twice(tmp_path: Path) -> None:
    root = _legacy_tree(tmp_path / "legacy")
    apply_attach(root)
    (root / ".mos" / "config.yaml").write_text(LEGACY_YAML, encoding="utf-8")
    planned = plan_attach(root)
    assert not any(change.startswith("backup") for change in planned["changes"])
    apply_attach(root)
    assert not (root / ".mos" / "config.legacy.1.yaml").exists()
    assert read_config(root)["business_name"] == "the-vibe-marketing-lab"


def test_client_mode_without_an_agency_warns_and_a_legacy_agency_is_kept(tmp_path: Path) -> None:
    bare = _legacy_tree(tmp_path / "bare", "mode: client\nname: acme\n")
    result = plan_attach(bare)
    assert result["ok"] is True
    warning = [item for item in result["findings"] if item["code"] == "legacy-agency-missing"]
    assert len(warning) == 1 and warning[0]["severity"] == "warning"
    assert warning[0]["path"] == ".mos/config.yaml"

    named = _legacy_tree(tmp_path / "named", "mode: client\nname: acme\nagency: Big HQ\n")
    result = apply_attach(named)
    assert not any(item["code"] == "legacy-agency-missing" for item in result["findings"])
    assert read_config(named)["agency"] == "Big HQ"

    inhouse = plan_attach(_legacy_tree(tmp_path / "inhouse"))
    assert not any(item["code"] == "legacy-agency-missing" for item in inhouse["findings"])


def test_canonical_brain_is_a_noop(tmp_path: Path) -> None:
    root = tmp_path / "canonical"
    setup_repo(root, "Canon Co", "all", mode="agency", apply=True)
    snapshot = _snapshot(root)
    result = plan_attach(root)
    assert result["ok"] is True
    assert result["changes"] == []
    assert result["findings"][0]["code"] == "already-attached"
    assert result["mode"] == "agency"
    assert result["next_action"]["id"] == "run-status"
    assert apply_attach(root)["changes"] == []
    assert _snapshot(root) == snapshot


def test_name_and_mode_overrides_win(tmp_path: Path) -> None:
    root = _legacy_tree(tmp_path / "legacy")
    result = apply_attach(root, name="The Lab", mode="agency")
    assert result["name"] == "The Lab"
    assert result["mode"] == "agency"
    config = json.loads((root / ".mos" / "config.yaml").read_text(encoding="utf-8"))
    assert config["business_name"] == "The Lab"
    assert config["mode"] == "agency"


def test_name_is_inferred_from_the_folder_without_a_config(tmp_path: Path) -> None:
    root = _legacy_tree(tmp_path / "acme-brain", config=None)
    result = plan_attach(root)
    assert result["ok"] is True
    assert result["name"] == "acme-brain"
    assert result["mode"] == "in-house"
    assert result["legacy"] is None
    assert "backup .mos/config.legacy.yaml" not in result["changes"]
    assert "config .mos/config.yaml" in result["changes"]


def test_business_name_key_beats_name_and_bad_legacy_mode_warns(tmp_path: Path) -> None:
    root = _legacy_tree(
        tmp_path / "legacy", config="name: slug-name\nbusiness_name: Proper Name\nmode: weird\n"
    )
    result = plan_attach(root)
    assert result["name"] == "Proper Name"
    assert result["mode"] == "in-house"
    assert any(item["code"] == "legacy-mode-ignored" for item in result["findings"])


def test_invalid_mode_missing_folder_and_plain_folder_are_refused(tmp_path: Path) -> None:
    root = _legacy_tree(tmp_path / "legacy")
    bad_mode = plan_attach(root, mode="weird")
    assert bad_mode["ok"] is False
    assert bad_mode["findings"][0]["code"] == "invalid-mode"

    missing = plan_attach(tmp_path / "nope")
    assert missing["ok"] is False
    assert missing["findings"][0]["code"] == "missing-directory"

    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "notes.txt").write_text("x", encoding="utf-8")
    refused = apply_attach(plain)
    assert refused["ok"] is False
    assert refused["findings"][0]["code"] == "not-a-brain"
    assert refused["next_action"]["id"] == "run-onboard"
    assert not (plain / ".mos").exists()


def test_legacy_summary_recognises_legacy_but_not_canonical_or_plain(tmp_path: Path) -> None:
    legacy = _legacy_tree(tmp_path / "legacy")
    assert legacy_summary(legacy) == {"name": "the-vibe-marketing-lab", "mode": "in-house"}
    canonical = tmp_path / "canonical"
    setup_repo(canonical, "Canon Co", "all", mode="in-house", apply=True)
    assert legacy_summary(canonical) is None
    plain = tmp_path / "plain"
    plain.mkdir()
    assert legacy_summary(plain) is None
