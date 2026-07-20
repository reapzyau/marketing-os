from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from marketing_os import __version__
from marketing_os.core.ingest import ingest_repo, pending_sources
from marketing_os.core.migrate import migrate_repo
from marketing_os.core.onboard import onboard_repo
from marketing_os.core.query import query_repo
from marketing_os.core.results import envelope, next_action
from marketing_os.core.setup import setup_repo
from marketing_os.core.skills import (
    apply_sync,
    global_manifest,
    plan_sync,
    project_manifest,
)
from marketing_os.core.status import doctor_repo, status_repo
from marketing_os.core.statusline import statusline_repo
from marketing_os.core.think import think_repo
from marketing_os.core.update import update_engine
from marketing_os.core.validation import validate_repo

RUNTIMES = ("claude", "codex", "all")
MODES = ("in-house", "agency", "client")


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _mutation_mode(args: argparse.Namespace) -> bool:
    if bool(args.plan) == bool(args.yes):
        raise ValueError("choose exactly one of --plan or --yes")
    return bool(args.yes)


def _add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", dest="json_out", help="Emit JSON only.")


def _add_mutation(parser: argparse.ArgumentParser, *, required: bool = True) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
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
    setup.add_argument(
        "--mode",
        choices=MODES,
        default=None,
        help="Repository mode: in-house (one brand you own), agency (serves clients; "
        "adds a client registry), or client (one agency client). Required.",
    )
    setup.add_argument(
        "--agency",
        default=None,
        help="Agency business name; required for --mode client, ignored otherwise.",
    )
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

    ingest = commands.add_parser("ingest", help="Capture raw material into knowledge/sources.")
    ingest.add_argument(
        "source",
        nargs="?",
        default=None,
        help="File, directory, URL, or text; requires --plan or --yes.",
    )
    ingest.add_argument("path", nargs="?", default=".")
    ingest.add_argument("--topic", default=None, help="Metadata-only topic label for the capture.")
    ingest.add_argument("--slug", default=None, help="Override the derived slug.")
    ingest.add_argument("--date", default=None, help="Capture date as YYYY-MM-DD (defaults today).")
    ingest.add_argument(
        "--pending",
        action="store_true",
        help="List captured sources not yet compiled "
        "(read-only; omit SOURCE and --plan/--yes; optional positional is the repo path).",
    )
    _add_mutation(ingest, required=False)
    _add_output(ingest)

    query = commands.add_parser("query", help="Plan deterministic retrieval for a question.")
    query.add_argument("question", help="The question to answer from the brain.")
    query.add_argument("path", nargs="?", default=".")
    query.add_argument("--limit", type=int, default=5, help="Maximum candidate documents.")
    _add_output(query)

    think = commands.add_parser("think", help="Emit a grounded thinking handoff for a topic.")
    think.add_argument("topic", help="The topic to reason about.")
    think.add_argument("path", nargs="?", default=".")
    _add_output(think)

    onboard = commands.add_parser("onboard", help="Scaffold a brain and hand off the interview.")
    onboard.add_argument("path", nargs="?", default=".")
    onboard.add_argument("--name", required=True, help="Business display name.")
    onboard.add_argument(
        "--mode",
        choices=MODES,
        default=None,
        help="Repository mode: in-house, agency, or client. Required.",
    )
    onboard.add_argument(
        "--agency",
        default=None,
        help="Agency business name; required for --mode client, ignored otherwise.",
    )
    onboard.add_argument(
        "--hq",
        default=None,
        help="Path to the agency HQ repo; in client mode appends a registry row there.",
    )
    onboard.add_argument("--runtime", choices=RUNTIMES, default="all")
    _add_mutation(onboard)
    _add_output(onboard)

    migrate = commands.add_parser(
        "migrate", help="Diagnose off-schema files or apply a deterministic routing plan."
    )
    migrate.add_argument("path", nargs="?", default=".")
    migrate.add_argument(
        "--plan-file",
        default=None,
        help="A mos.migrate-plan.v1 routing plan to preview or apply.",
    )
    _add_mutation(migrate)
    _add_output(migrate)

    update = commands.add_parser("update", help="Update the marketing-os engine itself.")
    _add_mutation(update)
    _add_output(update)

    statusline = commands.add_parser("statusline", help="Print a one-line ambient status badge.")
    statusline.add_argument("path", nargs="?", default=".")
    _add_output(statusline)
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
        return setup_repo(
            _path(args.path),
            args.name,
            args.runtime,
            mode=args.mode,
            agency=args.agency,
            apply=_mutation_mode(args),
        )
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
    if args.command == "ingest":
        if args.pending:
            if args.plan or args.yes:
                raise ValueError(
                    "--pending is read-only; do not combine it with --plan or --yes"
                )
            # --pending takes only an optional [path]; argparse fills `source` first,
            # so a lone positional is the path. Two positionals is ambiguous.
            if args.path != ".":
                raise ValueError("--pending takes only an optional PATH argument")
            where = args.source if args.source is not None else args.path
            return pending_sources(_path(where))
        if args.source is None:
            raise ValueError("ingest requires a SOURCE (or --pending to list captures)")
        return ingest_repo(
            _path(args.path),
            args.source,
            topic=args.topic,
            slug=args.slug,
            date=args.date,
            apply=_mutation_mode(args),
        )
    if args.command == "query":
        return query_repo(_path(args.path), args.question, limit=args.limit)
    if args.command == "think":
        return think_repo(_path(args.path), args.topic)
    if args.command == "onboard":
        return onboard_repo(
            _path(args.path),
            args.name,
            args.runtime,
            mode=args.mode,
            agency=args.agency,
            hq=_path(args.hq) if args.hq else None,
            apply=_mutation_mode(args),
        )
    if args.command == "migrate":
        return migrate_repo(
            _path(args.path), plan_file=args.plan_file, apply=_mutation_mode(args)
        )
    if args.command == "update":
        return update_engine(apply=_mutation_mode(args))
    if args.command == "statusline":
        return statusline_repo(_path(args.path))
    raise ValueError("unsupported command")


def _render_human(result: dict[str, Any]) -> str:
    state = "OK" if result["ok"] else "NEEDS ATTENTION"
    lines = [f"{state}: {result['command']}", f"Repository: {result['repo']}"]
    if result.get("mode"):
        lines.append(f"Mode: {result['mode']}")
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
    elif args.command == "statusline":
        line = result.get("line", "")
        if line:
            sys.stdout.write(line + "\n")
    else:
        sys.stdout.write(_render_human(result) + "\n")
    if args.command == "statusline":
        return 0
    return 0 if result["ok"] else 1


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
