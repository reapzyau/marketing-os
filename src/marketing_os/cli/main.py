from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from marketing_os import __version__
from marketing_os.core.results import envelope, next_action
from marketing_os.core.setup import setup_repo
from marketing_os.core.skills import (
    apply_sync,
    global_manifest,
    plan_sync,
    project_manifest,
)
from marketing_os.core.status import doctor_repo, status_repo
from marketing_os.core.validation import validate_repo

RUNTIMES = ("claude", "codex", "all")


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _mutation_mode(args: argparse.Namespace) -> bool:
    if bool(args.plan) == bool(args.yes):
        raise ValueError("choose exactly one of --plan or --yes")
    return bool(args.yes)


def _add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", dest="json_out", help="Emit JSON only.")


def _add_mutation(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", action="store_true", help="Preview changes without writing.")
    group.add_argument("--yes", action="store_true", help="Apply the reviewed changes.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mos", description="Manage a file-based marketing brain.")
    parser.add_argument("--version", action="version", version=f"mos {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    install = commands.add_parser("install", help="Install the three bootstrap skills globally.")
    install.add_argument("--runtime", choices=RUNTIMES, default="all")
    _add_mutation(install)
    _add_output(install)

    setup = commands.add_parser("setup", help="Plan or create a canonical business brain.")
    setup.add_argument("path", nargs="?", default=".")
    setup.add_argument("--name", required=True, help="Business display name.")
    setup.add_argument("--runtime", choices=RUNTIMES, default="all")
    _add_mutation(setup)
    _add_output(setup)

    status = commands.add_parser(
        "status", help="Inspect structure, context, and runtime readiness."
    )
    status.add_argument("path", nargs="?", default=".")
    _add_output(status)

    validate = commands.add_parser("validate", help="Validate the canonical schema and routing.")
    validate.add_argument("path", nargs="?", default=".")
    _add_output(validate)

    doctor = commands.add_parser("doctor", help="Check structure and both runtime adapters.")
    doctor.add_argument("path", nargs="?", default=".")
    _add_output(doctor)

    skills = commands.add_parser("skills", help="Manage generated runtime skill copies.")
    skill_commands = skills.add_subparsers(dest="skills_command", required=True)
    sync = skill_commands.add_parser("sync", help="Plan or synchronize project-local skills.")
    sync.add_argument("path", nargs="?", default=".")
    sync.add_argument("--runtime", choices=RUNTIMES, default="all")
    _add_mutation(sync)
    _add_output(sync)
    return parser


def _sync_result(root: Path, runtime: str, *, apply: bool, global_install: bool) -> dict[str, Any]:
    if global_install:
        manifest = global_manifest(root)
        target = root
        command = "install"
    else:
        manifest = project_manifest(root)
        target = root
        command = "skills-sync"
    actions, findings = plan_sync(target, runtime, manifest_path=manifest)
    if apply and not findings:
        apply_sync(actions, manifest)
    changes = [
        f"{item['action']} {Path(item['destination']).relative_to(target).as_posix()}"
        for item in actions
    ]
    if findings:
        action = next_action("resolve-skill-conflict", "Review the conflicting skill directories.")
    elif actions and not apply:
        action = next_action("apply-skill-sync", "Apply the reviewed skill synchronization plan.")
    else:
        action = next_action("run-start", "The shared skills are ready.")
    return envelope(
        command,
        root,
        ok=not findings,
        changes=changes,
        findings=findings,
        action=action,
        applied=apply and not findings,
        planned=not apply,
        runtime=runtime,
    )


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "install":
        return _sync_result(
            Path.home(), args.runtime, apply=_mutation_mode(args), global_install=True
        )
    if args.command == "setup":
        return setup_repo(_path(args.path), args.name, args.runtime, apply=_mutation_mode(args))
    if args.command == "status":
        return status_repo(_path(args.path))
    if args.command == "validate":
        return validate_repo(_path(args.path))
    if args.command == "doctor":
        return doctor_repo(_path(args.path))
    if args.command == "skills" and args.skills_command == "sync":
        return _sync_result(
            _path(args.path), args.runtime, apply=_mutation_mode(args), global_install=False
        )
    raise ValueError("unsupported command")


def _render_human(result: dict[str, Any]) -> str:
    state = "OK" if result["ok"] else "NEEDS ATTENTION"
    lines = [f"{state}: {result['command']}", f"Repository: {result['repo']}"]
    if result["changes"]:
        lines.append("Changes:")
        lines.extend(f"  - {change}" for change in result["changes"])
    if result["findings"]:
        lines.append("Findings:")
        lines.extend(
            f"  - [{item['severity']}] {item['message']}"
            + (f" ({item['path']})" if item.get("path") else "")
            for item in result["findings"]
        )
    lines.append(f"Next: {result['next_action']['reason']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = dispatch(args)
    except (OSError, ValueError) as exc:
        result = envelope(
            args.command or "error",
            Path.cwd(),
            ok=False,
            findings=[
                {
                    "code": "command-error",
                    "severity": "error",
                    "message": str(exc),
                    "path": "",
                }
            ],
            action=next_action("review-command", "Review the command and try again."),
        )
    if getattr(args, "json_out", False):
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(_render_human(result) + "\n")
    return 0 if result["ok"] else 1


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
