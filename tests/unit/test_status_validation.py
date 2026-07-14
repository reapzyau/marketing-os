from pathlib import Path

from marketing_os.core.setup import setup_repo
from marketing_os.core.status import status_repo
from marketing_os.core.validation import validate_repo


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
    setup_repo(root, "Example Business", "all", apply=True)
    validation = validate_repo(root)
    status = status_repo(root)
    assert validation["ok"] is True
    assert status["repo_state"] == "needs-context"
    assert status["context"]["missing"] == ["brand", "voice", "audience", "offer"]


def test_completed_context_becomes_ready(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", apply=True)
    _complete_context(root)
    status = status_repo(root)
    assert status["ok"] is True
    assert status["repo_state"] == "ready"
    assert status["context"]["ready"] is True


def test_invalid_dated_artifact_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", apply=True)
    invalid = root / "content" / "loose-file.md"
    invalid.write_text("wrong place", encoding="utf-8")
    validation = validate_repo(root)
    assert validation["ok"] is False
    assert any(item["code"] == "invalid-year" for item in validation["findings"])
