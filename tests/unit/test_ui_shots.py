"""The screenshot script builds its fixture brains somewhere disposable."""

import importlib.util
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ui_shots.py"


def _load():
    spec = importlib.util.spec_from_file_location("ui_shots", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_the_fixture_brains_are_built_under_the_temp_dir_not_home() -> None:
    """Three throwaway brains per viewport used to land in the operator's home folder and
    stay there. Now they go under the system temp dir and the run removes them."""
    shots = _load()
    root = shots.fixture_root()
    try:
        assert root.is_dir()
        assert root.name.startswith(shots.FIXTURE_PREFIX)
        assert Path(tempfile.gettempdir()).resolve() in root.resolve().parents
        assert root.resolve().parent != Path.home().resolve()
    finally:
        root.rmdir()
    assert not hasattr(shots, "BASE") and not hasattr(shots, "HOME")


def test_the_script_imports_without_a_browser_and_refuses_politely() -> None:
    shots = _load()
    if shots.sync_playwright is not None:
        return
    assert shots.main() == 2
