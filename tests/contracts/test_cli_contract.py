import json
from pathlib import Path

import pytest

from marketing_os.cli import main as cli_main
from marketing_os.cli.main import main
from marketing_os.core.results import envelope, next_action

REQUIRED_KEYS = {"schema", "command", "ok", "repo", "changes", "findings", "next_action"}


def _onboard(target: Path, *extra: str) -> None:
    main(
        [
            "onboard",
            str(target),
            "--name",
            "Example Business",
            "--mode",
            "in-house",
            *extra,
            "--json",
        ]
    )


def _make_repo(tmp_path: Path, capsys) -> Path:
    target = tmp_path / "brain"
    _onboard(target, "--yes")
    capsys.readouterr()
    return target


def test_onboard_json_envelope_and_plan(tmp_path: Path, capsys) -> None:
    target = tmp_path / "brain"
    code = main(
        [
            "onboard",
            str(target),
            "--name",
            "Example Business",
            "--mode",
            "in-house",
            "--runtime",
            "all",
            "--plan",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload.keys() >= REQUIRED_KEYS
    assert payload["schema"] == "mos.onboard.v1"
    assert payload["mode"] == "in-house"
    assert not target.exists()


def test_onboard_without_mode_returns_choose_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "brain"
    code = main(["onboard", str(target), "--name", "Example Business", "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["ok"] is False
    assert payload["next_action"]["id"] == "choose-mode"
    assert "--mode <choice>" in payload["next_action"]["reason"]
    assert not target.exists()


def test_failure_is_json_without_human_output(tmp_path: Path, capsys) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "notes.txt").write_text("existing", encoding="utf-8")
    code = main(
        [
            "onboard",
            str(target),
            "--name",
            "Example Business",
            "--runtime",
            "all",
            "--yes",
            "--json",
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert code == 1
    assert payload["ok"] is False
    assert output.lstrip().startswith("{")


def test_read_commands_share_envelope(tmp_path: Path, capsys) -> None:
    target = tmp_path / "brain"
    _onboard(target, "--yes")
    capsys.readouterr()
    for command in ("status", "validate", "doctor"):
        code = main([command, str(target), "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert code == 0
        assert payload.keys() >= REQUIRED_KEYS


def test_help_lists_all_commands(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    for command in (
        "install",
        "status",
        "validate",
        "doctor",
        "skills",
        "ingest",
        "query",
        "think",
        "onboard",
        "migrate",
        "update",
        "statusline",
    ):
        assert command in output


def test_ingest_envelope_and_pending(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(
        ["ingest", "a short captured note about pricing", str(target), "--yes", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema"] == "mos.ingest.v1"
    assert payload.keys() >= REQUIRED_KEYS
    assert payload["applied"] is True

    code = main(["ingest", "--pending", str(target), "--json"])
    pending = json.loads(capsys.readouterr().out)
    assert code == 0
    assert pending["schema"] == "mos.ingest-pending.v1"
    assert pending["command"] == "ingest-pending"
    assert pending["pending"]  # the fresh capture is not yet compiled


def test_ingest_plan_does_not_write(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["ingest", "literal planning text", str(target), "--plan", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["planned"] is True
    # The scaffold already contains knowledge/sources/; --plan must not write a capture.
    assert list((target / "knowledge" / "sources").rglob("source.md")) == []


def test_ingest_requires_source_or_pending(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["ingest", str(target), "--json"])
    payload = json.loads(capsys.readouterr().out)
    # With a single positional, it is read as SOURCE; without a mutation flag it fails.
    assert code == 1
    assert payload["ok"] is False


def test_ingest_missing_mutation_flag_is_rejected(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["ingest", "some text", str(target), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["ok"] is False
    assert payload["findings"][0]["code"] == "command-error"


def test_ingest_pending_rejects_source(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["ingest", "--pending", "unexpected", str(target), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["ok"] is False


def test_ingest_pending_with_yes_is_rejected(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["ingest", "--pending", str(target), "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["ok"] is False
    assert payload["findings"][0]["code"] == "command-error"


def test_ingest_pending_with_plan_is_rejected(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["ingest", "--pending", str(target), "--plan", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["ok"] is False
    assert payload["findings"][0]["code"] == "command-error"


def test_query_envelope(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["query", "what is the brand strategy", str(target), "--limit", "3", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema"] == "mos.query.v1"
    assert payload["question"] == "what is the brand strategy"
    assert "candidates" in payload


def test_think_envelope(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["think", "pricing model", str(target), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema"] == "mos.think.v1"
    assert payload["prompt"]["context_paths"]


def test_onboard_envelope_and_mutation_enforcement(tmp_path: Path, capsys) -> None:
    target = tmp_path / "fresh"
    code = main(
        ["onboard", str(target), "--name", "Fresh Co", "--mode", "in-house", "--yes", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema"] == "mos.onboard.v1"
    assert "interview" in payload
    assert payload["mode"] == "in-house"

    with pytest.raises(SystemExit) as exc:
        main(["onboard", str(target), "--name", "Fresh Co", "--mode", "in-house", "--json"])
    assert exc.value.code == 2


def test_help_lists_mode_flag(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["onboard", "--help"])
    output = capsys.readouterr().out
    assert "--mode" in output
    assert "--agency" in output


def test_update_envelope_is_monkeypatched(monkeypatch, capsys) -> None:
    def fake_update(*, apply: bool) -> dict:
        return envelope(
            "update",
            Path.cwd(),
            ok=True,
            changes=["noop"],
            action=next_action("run-doctor", "Verify the engine."),
            mode="pipx",
            run_command="noop",
            applied=apply,
            planned=not apply,
        )

    monkeypatch.setattr(cli_main, "update_engine", fake_update)
    code = main(["update", "--plan", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema"] == "mos.update.v1"
    assert payload["mode"] == "pipx"


def test_update_missing_mutation_flag_is_rejected() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["update", "--json"])
    assert exc.value.code == 2


def test_statusline_outside_repo_is_silent_and_zero(tmp_path: Path, capsys) -> None:
    code = main(["statusline", str(tmp_path)])
    output = capsys.readouterr().out
    assert code == 0
    assert output == ""


def test_statusline_active_prints_line(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["statusline", str(target)])
    output = capsys.readouterr().out
    assert code == 0
    assert output.startswith("mos")
    assert output.endswith("\n")


def test_statusline_json_envelope(tmp_path: Path, capsys) -> None:
    target = _make_repo(tmp_path, capsys)
    code = main(["statusline", str(target), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema"] == "mos.statusline.v1"
    assert payload["active"] is True
