from __future__ import annotations

from typing import Any

from .defaults import active_skill_name
from .overlay import build_skill_overlay
from .operations import list_project_conversations, load_state
from .workspace import TrailWorkspace


def build_manager_report(workspace: TrailWorkspace) -> dict[str, Any]:
    state = load_state(workspace)
    skill_name = active_skill_name(workspace)
    overlay = build_skill_overlay(workspace, skill_name, state=state) if skill_name else None
    conversations = list_project_conversations(workspace, limit=3)
    risk_items = [item.get("summary") or item.get("error_signature") for item in (state.get("open_blockers") or [])]
    risk_items.extend(item.get("error_signature") for item in (state.get("recent_failures") or []))
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
