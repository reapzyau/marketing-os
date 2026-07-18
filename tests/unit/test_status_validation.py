import json
from pathlib import Path

from marketing_os.core.setup import setup_repo
from marketing_os.core.status import doctor_repo, status_repo
from marketing_os.core.validation import validate_repo


def _rewrite_config(root: Path, **changes: object) -> None:
    config_path = root / ".mos" / "config.yaml"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for key, value in changes.items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _complete_context(root: Path) -> None:
    (root / "business/brand/brand.md").write_text(
        "# Brand\n\nWe make operational marketing systems understandable and durable.\n",
        encoding="utf-8",
    )
    (root / "business/brand/voice.md").write_text(
        "# Voice\n\nClear, direct, warm, specific, and free from inflated claims.\n",
        encoding="utf-8",
    )
    (root / "business/audience/primary.md").write_text(
        "# Audience\n\nSmall marketing teams that need reliable context across agent sessions.\n",
        encoding="utf-8",
    )
    offer = root / "business/offers/marketing-brain/offer.md"
    offer.parent.mkdir(parents=True)
    offer.write_text(
        "# Marketing Brain\n\n"
        "A file-based operating system that keeps agent work grounded and reusable.\n",
        encoding="utf-8",
    )


def test_fresh_repo_validates_but_requires_context(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", mode="in-house", apply=True)
    validation = validate_repo(root)
    status = status_repo(root)
    assert validation["ok"] is True
    assert status["repo_state"] == "needs-context"
    assert status["context"]["missing"] == ["brand", "voice", "audience", "offer"]


def test_completed_context_becomes_ready(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", mode="in-house", apply=True)
    _complete_context(root)
    status = status_repo(root)
    assert status["ok"] is True
    assert status["repo_state"] == "ready"
    assert status["context"]["ready"] is True


def test_invalid_dated_artifact_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", mode="in-house", apply=True)
    invalid = root / "content" / "loose-file.md"
    invalid.write_text("wrong place", encoding="utf-8")
    validation = validate_repo(root)
    assert validation["ok"] is False
    assert any(item["code"] == "invalid-year" for item in validation["findings"])


def test_agency_repo_validates_with_registry(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Agency", "all", mode="agency", apply=True)
    validation = validate_repo(root)
    assert validation["ok"] is True
    assert status_repo(root)["mode"] == "agency"


def test_agency_repo_without_registry_fails(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Agency", "all", mode="agency", apply=True)
    (root / "business" / "clients" / "clients.md").unlink()
    validation = validate_repo(root)
    assert validation["ok"] is False
    assert any(item["code"] == "missing-client-registry" for item in validation["findings"])


def test_in_house_repo_warns_on_unexpected_clients_folder(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", mode="in-house", apply=True)
    (root / "business" / "clients").mkdir()
    validation = validate_repo(root)
    assert validation["ok"] is True
    assert any(item["code"] == "unexpected-clients-folder" for item in validation["findings"])


def test_missing_mode_warns_but_stays_ok(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", mode="in-house", apply=True)
    _rewrite_config(root, mode=None)
    validation = validate_repo(root)
    assert validation["ok"] is True
    assert any(item["code"] == "missing-mode" for item in validation["findings"])
    assert status_repo(root)["mode"] == "in-house"


def test_legacy_repo_with_registry_suggests_agency(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    # Agency scaffold creates the client registry; stripping mode makes it a
    # legacy repo (implied in-house) that still carries the registry.
    setup_repo(root, "Example Agency", "all", mode="agency", apply=True)
    _rewrite_config(root, mode=None)
    validation = validate_repo(root)
    codes = [item["code"] for item in validation["findings"]]
    assert validation["ok"] is True
    assert "set-mode-agency" in codes
    assert "unexpected-clients-folder" not in codes


def test_invalid_mode_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", mode="in-house", apply=True)
    _rewrite_config(root, mode="franchise")
    validation = validate_repo(root)
    assert validation["ok"] is False
    assert any(item["code"] == "invalid-mode" for item in validation["findings"])


def test_doctor_reports_mode(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Agency", "all", mode="agency", apply=True)
    assert doctor_repo(root)["mode"] == "agency"
