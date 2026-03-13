from __future__ import annotations

from typing import Any

from .defaults import active_skill_name
from .overlay import build_skill_overlay
from .operations import list_project_conversations, load_state
from .migration import load_migration_pack
from .workspace import TrailWorkspace


def build_manager_report(workspace: TrailWorkspace) -> dict[str, Any]:
    state = load_state(workspace)
    skill_name = active_skill_name(workspace)
    overlay = build_skill_overlay(workspace, skill_name, state=state) if skill_name else None
    conversations = list_project_conversations(workspace, limit=3)
    risk_items = [item.get("summary") or item.get("error_signature") for item in (state.get("open_blockers") or [])]
    risk_items.extend(item.get("error_signature") for item in (state.get("recent_failures") or []))
    risk_items.extend(item.get("summary") for item in (state.get("recent_findings") or []) if item.get("status") in {"open", "needs_verification"})
    done_items = [item.get("summary") for item in (state.get("recent_decisions") or []) if item.get("summary")]
    if overlay:
        done_items.extend([f"Skill overlay active for {skill_name}", *[f"Pack active: {pack.get('title')}" for pack in overlay.get("packs") or []]])
    report = {
        "project_root": str(workspace.root),
        "goal": state.get("current_goal") or "No active goal recorded.",
        "in_progress": state.get("next_step") or "No next step recorded.",
        "done": [item for item in done_items[:8] if item],
        "risks": [item for item in risk_items[:8] if item],
        "next": state.get("next_step") or "No next step recorded.",
        "recent_conversations": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "status": item.get("status"),
                "updated_at": item.get("updated_at"),
            }
            for item in conversations
        ],
        "active_skill": skill_name,
        "active_overlay": overlay,
    }
    return report


def build_risk_register(workspace: TrailWorkspace) -> dict[str, Any]:
    state = load_state(workspace)
    risks: list[dict[str, Any]] = []
    for blocker in state.get("open_blockers") or []:
        risks.append(
            {
                "type": "blocker",
                "summary": blocker.get("summary"),
                "severity": blocker.get("severity") or "high",
                "owner": blocker.get("owner"),
            }
        )
    for finding in state.get("recent_findings") or []:
        if finding.get("status") in {"open", "needs_verification"}:
            risks.append(
                {
                    "type": "finding",
                    "summary": finding.get("summary"),
                    "severity": finding.get("severity") or "medium",
                    "owner": None,
                }
            )
    for failure in state.get("recent_failures") or []:
        risks.append(
            {
                "type": "failure",
                "summary": failure.get("error_signature"),
                "severity": "medium",
                "owner": None,
            }
        )
    return {
        "project_root": str(workspace.root),
        "goal": state.get("current_goal"),
        "next_step": state.get("next_step"),
        "risks": risks[:20],
    }


def _latest_handoff_path(workspace: TrailWorkspace) -> str | None:
    handoffs = sorted(workspace.handoffs_dir.glob("*.md"))
    if not handoffs:
        return None
    return str(handoffs[-1])


def build_resume_brief(workspace: TrailWorkspace) -> dict[str, Any]:
    state = load_state(workspace)
    skill_name = active_skill_name(workspace)
    conversations = list_project_conversations(workspace, limit=5)
    blockers = state.get("open_blockers") or []
    findings = state.get("recent_findings") or []
    open_findings = [item for item in findings if item.get("status") in {"open", "needs_verification"}]
    decisions = state.get("recent_decisions") or []
    failures = state.get("recent_failures") or []
    next_action = state.get("next_step") or "No next step recorded."
    report = {
        "project_root": str(workspace.root),
        "active_skill": skill_name,
        "goal": state.get("current_goal") or "No active goal recorded.",
        "next_step": next_action,
        "open_blockers": blockers[:5],
        "open_findings": open_findings[:5],
        "recent_decisions": decisions[-5:],
        "recent_failures": failures[-5:],
        "recent_conversations": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "status": item.get("status"),
                "updated_at": item.get("updated_at"),
            }
            for item in conversations
        ],
        "latest_handoff": _latest_handoff_path(workspace),
        "recommended_next_action": next_action,
    }
    return report


def build_audit_report(workspace: TrailWorkspace) -> dict[str, Any]:
    state = load_state(workspace)
    migration_pack = load_migration_pack(workspace) or {}
    findings = state.get("recent_findings") or []
    status_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for item in findings:
        status = (item.get("status") or "unspecified").lower()
        severity = (item.get("severity") or "unspecified").lower()
        category = (item.get("category") or "general").lower()
        status_counts[status] = status_counts.get(status, 0) + 1
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1

    top_open = [
        item
        for item in findings
        if item.get("status") in {"open", "needs_verification"}
    ][:8]
    blockers = state.get("open_blockers") or []
    report = {
        "project_root": str(workspace.root),
        "goal": state.get("current_goal") or "No active goal recorded.",
        "next_step": state.get("next_step") or "No next step recorded.",
        "migration_pack": {
            "kind": migration_pack.get("kind"),
            "skill_name": migration_pack.get("skill_name"),
            "agent_name": migration_pack.get("agent_name"),
            "sources": migration_pack.get("sources") or [],
            "statuses": migration_pack.get("statuses") or [],
        }
        if migration_pack
        else None,
        "findings_total": len(findings),
        "status_counts": status_counts,
        "severity_counts": severity_counts,
        "category_counts": category_counts,
        "open_blockers": blockers[:8],
        "top_open_findings": top_open,
        "recent_decisions": (state.get("recent_decisions") or [])[-5:],
    }
    return report


def render_manager_report(report: dict[str, Any]) -> str:
    lines = [
        "Manager report",
        f"- Goal: {report.get('goal')}",
        f"- In progress: {report.get('in_progress')}",
        f"- Next: {report.get('next')}",
        f"- Active skill: {report.get('active_skill') or 'none'}",
        "- Done:",
    ]
    done = report.get("done") or []
    if done:
        lines.extend([f"  - {item}" for item in done])
    else:
        lines.append("  - None recorded")
    lines.append("- Risks:")
    risks = report.get("risks") or []
    if risks:
        lines.extend([f"  - {item}" for item in risks])
    else:
        lines.append("  - None recorded")
    lines.append("- Recent conversations:")
    conversations = report.get("recent_conversations") or []
    if conversations:
        lines.extend([f"  - {item['id']} ({item['status']}): {item['title']}" for item in conversations])
    else:
        lines.append("  - None recorded")
    return "\n".join(lines)


def render_resume_brief(report: dict[str, Any]) -> str:
    lines = [
        "Resume brief",
        f"- Project: {report.get('project_root')}",
        f"- Active skill: {report.get('active_skill') or 'none'}",
        f"- Goal: {report.get('goal')}",
        f"- Next: {report.get('next_step')}",
        f"- Recommended next action: {report.get('recommended_next_action')}",
        f"- Latest handoff: {report.get('latest_handoff') or 'none'}",
        "- Open blockers:",
    ]
    blockers = report.get("open_blockers") or []
    if blockers:
        lines.extend([f"  - {item.get('summary')}" for item in blockers])
    else:
        lines.append("  - None recorded")
    lines.append("- Open findings:")
    findings = report.get("open_findings") or []
    if findings:
        lines.extend(
            [
                f"  - [{item.get('severity') or 'medium'} / {item.get('status') or 'open'}] {item.get('summary')}"
                for item in findings
            ]
        )
    else:
        lines.append("  - None recorded")
    lines.append("- Recent decisions:")
    decisions = report.get("recent_decisions") or []
    if decisions:
        lines.extend([f"  - {item.get('summary')}" for item in decisions])
    else:
        lines.append("  - None recorded")
    return "\n".join(lines)


def render_audit_report(report: dict[str, Any]) -> str:
    migration_pack = report.get("migration_pack") or {}
    lines = [
        "Audit report",
        f"- Project: {report.get('project_root')}",
        f"- Goal: {report.get('goal')}",
        f"- Next: {report.get('next_step')}",
        f"- Audit skill: {migration_pack.get('skill_name') or 'none'}",
        f"- Audit agent: {migration_pack.get('agent_name') or 'none'}",
        f"- Sources: {len(migration_pack.get('sources') or [])}",
        f"- Findings total: {report.get('findings_total') or 0}",
        "- Status counts:",
    ]
    for key, value in sorted((report.get("status_counts") or {}).items()):
        lines.append(f"  - {key}: {value}")
    if not report.get("status_counts"):
        lines.append("  - None recorded")
    lines.append("- Open blockers:")
    blockers = report.get("open_blockers") or []
    if blockers:
        lines.extend([f"  - {item.get('summary')}" for item in blockers])
    else:
        lines.append("  - None recorded")
    lines.append("- Top open findings:")
    findings = report.get("top_open_findings") or []
    if findings:
        lines.extend(
            [
                f"  - [{item.get('severity') or 'medium'} / {item.get('status') or 'open'}] {item.get('summary')}"
                for item in findings
            ]
        )
    else:
        lines.append("  - None recorded")
    return "\n".join(lines)
