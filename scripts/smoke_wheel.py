from __future__ import annotations

import json
import os
import subprocess
import tempfile
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def executable(environment: Path, name: str) -> Path:
    folder = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return environment / folder / f"{name}{suffix}"


def main() -> int:
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one built wheel in dist/.")
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        skill_files = sorted(
            name
            for name in archive.namelist()
            if "/assets/skills/" in name and name.endswith("/SKILL.md")
        )
        if len(skill_files) != 9:
            raise RuntimeError("The wheel must contain exactly nine skills.")
        if not any(
            name.endswith("/assets/business-template/.gitignore") for name in archive.namelist()
        ):
            raise RuntimeError("The wheel is missing the generated repository ignore contract.")
        if not any(
            name.endswith("/assets/mode-overlays/agency/business/clients/clients.md")
            for name in archive.namelist()
        ):
            raise RuntimeError("The wheel is missing the agency mode overlay.")

    with tempfile.TemporaryDirectory(prefix="mos-wheel-smoke-") as temp:
        temp_root = Path(temp)
        environment = temp_root / "venv"
        brain = temp_root / "business"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = executable(environment, "python")
        mos = executable(environment, "mos")
        run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)])
        plan = json.loads(
            run(
                [
                    str(mos),
                    "setup",
                    str(brain),
                    "--name",
                    "Wheel Smoke",
                    "--mode",
                    "agency",
                    "--runtime",
                    "all",
                    "--plan",
                    "--json",
                ]
            ).stdout
        )
        if not plan["ok"] or brain.exists():
            raise RuntimeError("Setup planning must succeed without creating the destination.")
        apply = json.loads(
            run(
                [
                    str(mos),
                    "setup",
                    str(brain),
                    "--name",
                    "Wheel Smoke",
                    "--mode",
                    "agency",
                    "--runtime",
                    "all",
                    "--yes",
                    "--json",
                ]
            ).stdout
        )
        validate = json.loads(run([str(mos), "validate", str(brain), "--json"]).stdout)
        doctor = json.loads(run([str(mos), "doctor", str(brain), "--json"]).stdout)
        if not apply["ok"] or not validate["ok"] or not doctor["ok"]:
            raise RuntimeError("The installed wheel did not create a healthy business repository.")
        if not (brain / "business" / "clients" / "clients.md").is_file():
            raise RuntimeError("Agency setup did not scaffold the client registry overlay.")
        for runtime_dir in (".claude", ".agents"):
            for skill in (
                "mos-setup",
                "mos-start",
                "mos-help",
                "mos-status",
                "mos-end",
                "mos-think",
                "mos-bet",
                "mos-update",
                "mos-onboard",
            ):
                if not (brain / runtime_dir / "skills" / skill / "SKILL.md").is_file():
                    raise RuntimeError(f"Missing generated skill: {runtime_dir}/{skill}")
    print("wheel smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
