import json
from pathlib import Path

from marketing_os.core.migrate import PLAN_SCHEMA, migrate_repo
from marketing_os.core.setup import setup_repo


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", mode="in-house", apply=True)
    return root


def _write_plan(tmp_path: Path, plan: dict) -> Path:
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    return plan_file


def test_diagnose_lists_stray_entries(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "old-notes.md").write_text("stray", encoding="utf-8")
    (root / "legacy").mkdir()
    result = migrate_repo(root, apply=False)
    assert result["ok"] is True
    assert set(result["unrouted"]) == {"old-notes.md", "legacy"}
    assert result["plan_schema"] == PLAN_SCHEMA


def test_apply_moves_stray_file_into_canonical_location(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "launch.md").write_text("# Launch", encoding="utf-8")
    plan = {
        "schema": PLAN_SCHEMA,
        "mkdirs": ["content/2026/07"],
        "moves": [
            {"source": "launch.md", "destination": "content/2026/07/2026-07-15-launch/launch.md"}
        ],
    }
    result = migrate_repo(root, plan_file=str(_write_plan(tmp_path, plan)), apply=True)
    assert result["ok"] is True
    assert result["moved"] == 1
    assert not (root / "launch.md").exists()
    assert (root / "content/2026/07/2026-07-15-launch/launch.md").read_text() == "# Launch"


def test_plan_preview_does_not_write(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "launch.md").write_text("# Launch", encoding="utf-8")
    plan = {
        "schema": PLAN_SCHEMA,
        "moves": [{"source": "launch.md", "destination": "outputs/launch.md"}],
    }
    result = migrate_repo(root, plan_file=str(_write_plan(tmp_path, plan)), apply=False)
    assert result["planned"] is True
    assert result["changes"]
    assert (root / "launch.md").exists()
    assert not (root / "outputs/launch.md").exists()


def test_apply_requires_plan_file(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    result = migrate_repo(root, apply=True)
    assert result["ok"] is False
    assert result["findings"][0]["code"] == "missing-plan-file"


def test_refuses_destination_outside_repo(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "secret.md").write_text("x", encoding="utf-8")
    plan = {
        "schema": PLAN_SCHEMA,
        "moves": [{"source": "secret.md", "destination": "../escaped.md"}],
    }
    result = migrate_repo(root, plan_file=str(_write_plan(tmp_path, plan)), apply=True)
    assert result["ok"] is False
    assert any(f["code"] == "destination-outside-repo" for f in result["findings"])
    assert (root / "secret.md").exists()
    assert not (tmp_path / "escaped.md").exists()


def test_refuses_to_overwrite_existing_destination(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "voice-notes.md").write_text("new", encoding="utf-8")
    plan = {
        "schema": PLAN_SCHEMA,
        "moves": [{"source": "voice-notes.md", "destination": "business/brand/voice.md"}],
    }
    result = migrate_repo(root, plan_file=str(_write_plan(tmp_path, plan)), apply=True)
    assert result["ok"] is False
    assert any(f["code"] == "destination-exists" for f in result["findings"])
    assert (root / "voice-notes.md").read_text() == "new"


def test_invalid_move_is_atomic(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "good.md").write_text("good", encoding="utf-8")
    plan = {
        "schema": PLAN_SCHEMA,
        "moves": [
            {"source": "good.md", "destination": "outputs/good.md"},
            {"source": "missing.md", "destination": "outputs/missing.md"},
        ],
    }
    result = migrate_repo(root, plan_file=str(_write_plan(tmp_path, plan)), apply=True)
    assert result["ok"] is False
    assert any(f["code"] == "missing-source" for f in result["findings"])
    # Atomic: the valid move must not have run because a sibling move was invalid.
    assert (root / "good.md").exists()
    assert not (root / "outputs/good.md").exists()


def test_unsupported_plan_schema_is_rejected(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    plan_file = _write_plan(tmp_path, {"schema": "something.else", "moves": []})
    result = migrate_repo(root, plan_file=str(plan_file), apply=True)
    assert result["ok"] is False
    assert result["findings"][0]["code"] == "unsupported-plan"


def test_missing_plan_file_is_reported(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    result = migrate_repo(root, plan_file=str(tmp_path / "nope.json"), apply=True)
    assert result["ok"] is False
    assert result["findings"][0]["code"] == "missing-plan-file"


def test_migrate_envelope_is_json_serialisable(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    payload = json.loads(json.dumps(migrate_repo(root, apply=False)))
    assert payload["schema"] == "mos.migrate.v1"
    assert payload["command"] == "migrate"
