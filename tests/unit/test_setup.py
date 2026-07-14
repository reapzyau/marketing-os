from pathlib import Path

from marketing_os.core.setup import setup_repo


def test_setup_plan_is_non_mutating(tmp_path: Path) -> None:
    target = tmp_path / "brain"
    result = setup_repo(target, "Example Business", "all", apply=False)
    assert result["ok"] is True
    assert result["planned"] is True
    assert result["changes"]
    assert not target.exists()


def test_setup_apply_and_repeat_are_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "brain"
    first = setup_repo(target, "Example Business", "all", apply=True)
    before = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }
    second = setup_repo(target, "Example Business", "all", apply=True)
    after = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }
    assert first["ok"] is True
    assert first["changes"]
    assert second["ok"] is True
    assert second["changes"] == []
    assert after == before


def test_setup_never_overwrites_business_truth(tmp_path: Path) -> None:
    target = tmp_path / "brain"
    setup_repo(target, "Example Business", "all", apply=True)
    voice = target / "business" / "brand" / "voice.md"
    voice.write_text("# Voice\n\nA deliberately specific voice.\n", encoding="utf-8")
    setup_repo(target, "Example Business", "all", apply=True)
    assert voice.read_text(encoding="utf-8") == "# Voice\n\nA deliberately specific voice.\n"


def test_setup_refuses_nonempty_unidentified_directory(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "notes.md").write_text("existing", encoding="utf-8")
    result = setup_repo(target, "Example Business", "all", apply=True)
    assert result["ok"] is False
    assert result["findings"][0]["code"] == "unsupported-directory"
    assert not (target / "BRAIN.md").exists()
