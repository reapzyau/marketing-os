from __future__ import annotations

from pathlib import Path
from typing import Any

from marketing_os.core.results import envelope, finding, next_action
from marketing_os.core.schema import config_text, read_config, template_root
from marketing_os.core.skills import apply_sync, plan_sync, project_manifest


def _render(text: str, name: str) -> str:
    return text.replace("{{BUSINESS_NAME}}", name.strip())


def _template_actions(target: Path, name: str) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    root = template_root()
    for source in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = source.relative_to(root)
        destination = target / relative
        if destination.exists():
            continue
        actions.append(
            {
                "source": str(source),
                "destination": str(destination),
                "relative": relative.as_posix(),
            }
        )
    config = target / ".mos" / "config.yaml"
    if not config.exists():
        actions.append(
            {
                "source": "",
                "destination": str(config),
                "relative": ".mos/config.yaml",
                "content": config_text(name),
            }
        )
    return actions


def _apply_templates(actions: list[dict[str, str]], name: str) -> None:
    for action in actions:
        destination = Path(action["destination"])
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if "content" in action:
            text = action["content"]
        else:
            text = Path(action["source"]).read_text(encoding="utf-8")
        destination.write_text(_render(text, name), encoding="utf-8")


def setup_repo(target: Path, name: str, runtime: str, *, apply: bool) -> dict[str, Any]:
    target = target.expanduser().resolve()
    findings: list[dict[str, str]] = []
    if not name.strip():
        findings.append(finding("missing-name", "Business name must not be empty."))
    if target.exists() and any(target.iterdir()) and read_config(target) is None:
        findings.append(
            finding(
                "unsupported-directory",
                "The destination is non-empty and is not a marketing-os repository. "
                "Use a new empty destination.",
                path=str(target),
            )
        )
    if findings:
        return envelope(
            "setup",
            target,
            ok=False,
            findings=findings,
            action=next_action(
                "choose-empty-destination", "Choose an empty folder for the new business brain."
            ),
            applied=False,
        )

    file_actions = _template_actions(target, name)
    skill_actions, skill_findings = plan_sync(
        target, runtime, manifest_path=project_manifest(target)
    )
    findings.extend(skill_findings)
    changes = [f"create {item['relative']}" for item in file_actions]
    changes.extend(
        f"{item['action']} {Path(item['destination']).relative_to(target).as_posix()}"
        for item in skill_actions
    )
    if apply and not findings:
        target.mkdir(parents=True, exist_ok=True)
        _apply_templates(file_actions, name)
        apply_sync(skill_actions, project_manifest(target))

    ok = not findings
    action = next_action(
        "apply-setup" if not apply and changes else "complete-context",
        "Apply the reviewed setup plan."
        if not apply and changes
        else "Complete the audience, offer, and voice context with the setup skill.",
    )
    if apply and not changes:
        action = next_action("run-start", "The repository is already scaffolded and wired.")
    return envelope(
        "setup",
        target,
        ok=ok,
        changes=changes,
        findings=findings,
        action=action,
        applied=apply and ok,
        planned=not apply,
    )
