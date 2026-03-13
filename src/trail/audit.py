from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .defaults import active_packs, active_skill_name
from .events import emit_event
from .migration import load_migration_pack
from .overlay import build_skill_overlay
from .packs import load_pack
from .workspace import TrailWorkspace


def record_finding(
    workspace: TrailWorkspace,
    *,
    summary: str,
    severity: str | None = None,
    status: str | None = None,
    category: str | None = None,
    source: str | None = None,
    evidence: str | None = None,
    recommendation: str | None = None,
) -> dict[str, Any]:
    return emit_event(
        workspace,
        session_id="manual",
        kind="finding_recorded",
        payload={
            "summary": summary,
            "severity": severity or "medium",
            "status": status or "open",
            "category": category or "audit",
            "source": source,
            "evidence": evidence,
            "recommendation": recommendation,
        },
    )


def _active_pack_records(workspace: TrailWorkspace) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for slug in active_packs(workspace):
        pack = load_pack(workspace, slug)
        if pack:
            records.append(pack)
    return records


def build_audit_screen_prompt(
    workspace: TrailWorkspace,
    *,
    screen: str,
    task: str | None = None,
    state: dict[str, Any],
) -> str:
    skill_name = active_skill_name(workspace)
    overlay = build_skill_overlay(workspace, skill_name, state=state) if skill_name else None
    migration_pack = load_migration_pack(workspace)
    packs = _active_pack_records(workspace)
    lines = [
        "You are auditing a migrated screen with Trail context.",
        f"Target screen or flow: {screen}",
        "",
        "Audit objectives:",
        "- verify legacy business rules are preserved",
        "- verify EUI21 / ECL21 conventions are respected",
        "- separate visible polish from runtime correctness",
        "",
        f"Project root: {workspace.root}",
        f"Active goal: {state.get('current_goal') or 'No active goal recorded.'}",
        f"Next step: {state.get('next_step') or 'No next step recorded.'}",
    ]
    if overlay:
        if overlay.get("project_summary"):
            lines.append(f"Overlay summary: {overlay['project_summary']}")
        if overlay.get("current_focus"):
            lines.append(f"Overlay focus: {overlay['current_focus']}")
        if overlay.get("directives"):
            lines.append("Dynamic directives:")
            for item in overlay["directives"][:8]:
                lines.append(f"- {item}")
    if migration_pack:
        lines.append("Migration pack is active. Use its retained rules, gaps, and critical flows.")
    if packs:
        lines.append("Active packs:")
        for pack in packs[:6]:
            lines.append(f"- {pack.get('title')} ({pack.get('kind')}): {pack.get('summary')}")
    lines.extend(
        [
            "",
            "Required output:",
            "1. compliant items",
            "2. gaps",
            "3. needs verification",
            "4. exact next step",
            "",
            "Trail actions:",
            "- use Trail search before assuming rules or conventions",
            "- record confirmed findings and blockers back into Trail",
            "",
            "User task:",
            task or f"Audit the screen or flow `{screen}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_audit_diff_prompt(
    workspace: TrailWorkspace,
    *,
    diff_text: str,
    base_ref: str,
    paths: list[str],
    task: str | None,
    state: dict[str, Any],
) -> str:
    skill_name = active_skill_name(workspace)
    overlay = build_skill_overlay(workspace, skill_name, state=state) if skill_name else None
    migration_pack = load_migration_pack(workspace)
    lines = [
        "You are reviewing a diff with Trail context.",
        f"Base ref: {base_ref}",
        f"Paths: {', '.join(paths) if paths else 'all changed files'}",
        "",
        "Review priorities:",
        "- business rule regressions",
        "- EUI21 / ECL21 convention regressions",
        "- runtime-risk changes",
        "- migration parity gaps",
        "",
        f"Project root: {workspace.root}",
        f"Active goal: {state.get('current_goal') or 'No active goal recorded.'}",
        f"Next step: {state.get('next_step') or 'No next step recorded.'}",
    ]
    if overlay and overlay.get("directives"):
        lines.append("Dynamic directives:")
        for item in overlay["directives"][:8]:
            lines.append(f"- {item}")
    if overlay and overlay.get("avoid"):
        lines.append("Do not miss:")
        for item in overlay["avoid"][:6]:
            lines.append(f"- {item}")
    if migration_pack:
        lines.append("Migration pack is active. Use it to judge parity and risk.")
    lines.extend(
        [
            "",
            "Required output:",
            "1. critical findings",
            "2. medium findings",
            "3. things that still need runtime verification",
            "4. exact recommendation",
            "",
            "Diff under review:",
            diff_text.strip() or "(empty diff)",
            "",
            "User task:",
            task or "Review the diff against Trail context.",
        ]
    )
    return "\n".join(lines) + "\n"


def get_git_diff(workspace: TrailWorkspace, *, base_ref: str, paths: list[str]) -> str:
    command = ["git", "diff", "--stat=200", "--unified=3", base_ref]
    if paths:
        command.extend(["--", *paths])
    try:
        result = subprocess.run(
            command,
            cwd=workspace.root,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git is required for `trail audit diff`") from exc
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return result.stdout
