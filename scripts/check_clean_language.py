from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".toml", ".json", ".yaml", ".yml", ".txt"}

BLOCKED = [
    re.compile(r"\b" + "m" + "b" + r"\b", re.IGNORECASE),
    re.compile("main" + "branch", re.IGNORECASE),
    re.compile(re.escape("." + "m" + "b"), re.IGNORECASE),
    re.compile(re.escape("." + "v" + "ip"), re.IGNORECASE),
    re.compile(re.escape("." + "Code" + "x")),
]
RETIRED_COMMANDS = ["mos " + suffix for suffix in ("connect", "ads", "site", "image")]


def source_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in completed.stdout.splitlines() if line]


def main() -> int:
    violations: list[str] = []
    files = source_files()
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith((".claude/skills/", ".agents/skills/")):
            violations.append(f"tracked generated skill catalog: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"LICENSE", ".gitignore"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in BLOCKED:
            if pattern.search(text):
                violations.append(f"blocked inherited identifier: {relative}")
        for command in RETIRED_COMMANDS:
            if command in text:
                violations.append(f"retired command: {relative}")
    if violations:
        print("\n".join(sorted(set(violations))))
        return 1
    print("clean-language gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
