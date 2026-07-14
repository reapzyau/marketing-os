from pathlib import Path

from marketing_os.core.setup import setup_repo
from marketing_os.core.skills import bundled_skills, inspect_runtimes


def test_fresh_repo_exposes_all_skills_to_both_adapters(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    setup_repo(root, "Runtime Smoke", "all", apply=True)
    runtimes = inspect_runtimes(root)
    for runtime in ("claude", "codex"):
        assert runtimes[runtime]["ready"] is True
        for skill in bundled_skills():
            skill_file = (
                root
                / (".claude" if runtime == "claude" else ".agents")
                / "skills"
                / skill
                / "SKILL.md"
            )
            assert skill_file.is_file()
            assert f"name: {skill}" in skill_file.read_text(encoding="utf-8")
