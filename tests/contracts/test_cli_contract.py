import json
from pathlib import Path

from marketing_os.cli.main import main

REQUIRED_KEYS = {"schema", "command", "ok", "repo", "changes", "findings", "next_action"}


def test_setup_json_envelope_and_plan(tmp_path: Path, capsys) -> None:
    target = tmp_path / "brain"
    code = main(
        ["setup", str(target), "--name", "Example Business", "--runtime", "all", "--plan", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload.keys() >= REQUIRED_KEYS
    assert payload["schema"] == "mos.setup.v1"
    assert not target.exists()


def test_failure_is_json_without_human_output(tmp_path: Path, capsys) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "notes.txt").write_text("existing", encoding="utf-8")
    code = main(
        ["setup", str(target), "--name", "Example Business", "--runtime", "all", "--yes", "--json"]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert code == 1
    assert payload["ok"] is False
    assert output.lstrip().startswith("{")


def test_read_commands_share_envelope(tmp_path: Path, capsys) -> None:
    target = tmp_path / "brain"
    main(["setup", str(target), "--name", "Example Business", "--yes", "--json"])
    capsys.readouterr()
    for command in ("status", "validate", "doctor"):
        code = main([command, str(target), "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert code == 0
        assert payload.keys() >= REQUIRED_KEYS
