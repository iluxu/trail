from __future__ import annotations

from pathlib import Path
from typing import Any

from .events import emit_event, utc_now
from .registry import global_registry, project_record_id, skill_record_id, slugify
from .reducer import reduce_state
from .skills import build_skill_briefing, resolve_skill
from .workspace import TrailWorkspace


def init_workspace(workspace: TrailWorkspace) -> None:
    workspace.ensure()
    if not workspace.current_state_path.exists():
        reduce_state(workspace)


def load_state(workspace: TrailWorkspace) -> dict[str, Any]:
    init_workspace(workspace)
    return reduce_state(workspace)


def current_session_id(workspace: TrailWorkspace) -> str:
    current = workspace.read_json(workspace.current_session_path) or {}
    return current.get("session_id") or "manual"


def current_conversation(workspace: TrailWorkspace) -> dict[str, Any]:
    return workspace.read_json(workspace.current_conversation_path) or {}


def create_or_update_conversation(
    workspace: TrailWorkspace,
    *,
    conversation_id: str,
    session_id: str,
    project_id: str,
    skill_id: str | None,
    title: str,
    current_goal: str | None,
    next_step: str | None,
    status: str,
    transcript_ref: str | None = None,
) -> dict[str, Any]:
    now = utc_now()
    existing = workspace.read_json(workspace.conversations_dir / f"{conversation_id}.json") or {}
    conversation = {
        "id": conversation_id,
        "session_id": session_id,
        "project_id": project_id,
        "skill_ids": [skill_id] if skill_id else [],
        "title": title,
        "status": status,
        "started_at": existing.get("started_at") or now,
        "updated_at": now,
        "current_goal": current_goal,
        "summary": existing.get("summary"),
        "next_step": next_step,
        "blockers": existing.get("blockers") or [],
        "transcript_ref": transcript_ref or existing.get("transcript_ref"),
        "handoff_refs": existing.get("handoff_refs") or [],
        "tags": existing.get("tags") or [],
    }
    path = workspace.conversations_dir / f"{conversation_id}.json"
    workspace.write_json(path, conversation)
    workspace.write_json(workspace.current_conversation_path, conversation)
    return conversation


def sync_conversation_to_registry(workspace: TrailWorkspace, conversation: dict[str, Any]) -> dict[str, Any]:
    registry = global_registry()
    payload = {
        **conversation,
        "root": str(workspace.root),
    }
    return registry.upsert_conversation(payload)


def fetch_conversation_to_workspace(workspace: TrailWorkspace, conversation_id: str) -> dict[str, Any]:
    registry = global_registry()
    conversation = registry.get_conversation(conversation_id)
    if not conversation:
        raise FileNotFoundError(f"Conversation not found: {conversation_id}")
    local_path = workspace.conversations_dir / f"{conversation['id']}.json"
    workspace.write_json(local_path, conversation)
    workspace.write_json(workspace.current_conversation_path, conversation)
    return conversation


def list_project_conversations(
    workspace: TrailWorkspace,
    *,
    project_identifier: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    registry = global_registry()
    project = registry.get_project(project_identifier) if project_identifier else registry.get_project_by_root(workspace.root)
    items = registry.list_conversations()
    if project:
        items = [item for item in items if item.get("project_id") == project.get("id")]
    items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return items[: max(1, min(limit, 50))]


def get_registered_conversation(conversation_id: str) -> dict[str, Any] | None:
    registry = global_registry()
    return registry.get_conversation(conversation_id)


def build_context_pack(
    workspace: TrailWorkspace,
    *,
    skill_name: str | None = None,
    user_task: str | None = None,
) -> dict[str, Any]:
    state = load_state(workspace)
    conversation = current_conversation(workspace)
    registry = global_registry()
    project_record = registry.get_project_by_root(workspace.root)
    skill = resolve_skill(skill_name) if skill_name else None
    skill_record = registry.get_skill(skill.name) if skill else None
    briefing = build_skill_briefing(workspace, skill, state, user_task) if skill else None
    project_id = project_record["id"] if project_record else project_record_id(slugify(workspace.root.name))
    skill_id = skill_record["id"] if skill_record else (skill_record_id(slugify(skill.name)) if skill else None)
    linked_conversation_ids: list[str] = []
    if project_record:
        linked_conversation_ids.extend(project_record.get("linked_conversations") or [])
    if skill_record:
        linked_conversation_ids.extend(skill_record.get("linked_conversations") or [])
    linked_conversations = []
    seen_conversations: set[str] = set()
    for conversation_id in linked_conversation_ids:
        if conversation_id in seen_conversations:
            continue
        seen_conversations.add(conversation_id)
        record = registry.get_conversation(conversation_id)
        if record:
            linked_conversations.append(record)
    linked_agents = []
    if project_record:
        for agent in registry.list_agents():
            if project_record["id"] in (agent.get("linked_projects") or []):
                linked_agents.append(agent)
    context = {
        "project_id": project_id,
        "project_root": str(workspace.root),
        "project": project_record,
        "conversation_id": conversation.get("id"),
        "conversation": registry.get_conversation(conversation.get("id")) if conversation.get("id") else None,
        "linked_conversations": linked_conversations[-10:],
        "linked_agents": linked_agents[-10:],
        "skill_id": skill_id,
        "skill": skill_record,
        "goal": state.get("current_goal"),
        "current_state": f"Event count: {state.get('event_count', 0)}",
        "next_step": state.get("next_step"),
        "open_blockers": state.get("open_blockers") or [],
        "recent_decisions": state.get("recent_decisions") or [],
        "recent_failures": state.get("recent_failures") or [],
        "briefing": briefing,
    }
    workspace.write_json(workspace.current_context_path, context)
    return context


def record_decision(
    workspace: TrailWorkspace,
    *,
    summary: str,
    reason: str | None = None,
    impact: str | None = None,
) -> dict[str, Any]:
    event = emit_event(
        workspace,
        session_id=current_session_id(workspace),
        kind="decision_made",
        payload={"summary": summary, "reason": reason, "impact": impact},
    )
    reduce_state(workspace)
    return event


def record_blocker(
    workspace: TrailWorkspace,
    *,
    summary: str,
    blocker_id: str | None = None,
    severity: str | None = None,
    owner: str | None = None,
    workaround: str | None = None,
) -> dict[str, Any]:
    event = emit_event(
        workspace,
        session_id=current_session_id(workspace),
        kind="blocker_opened",
        payload={
            "id": blocker_id,
            "summary": summary,
            "severity": severity,
            "owner": owner,
            "workaround": workaround,
        },
    )
    reduce_state(workspace)
    return event


def record_next_step(workspace: TrailWorkspace, *, summary: str) -> dict[str, Any]:
    event = emit_event(
        workspace,
        session_id=current_session_id(workspace),
        kind="next_step_set",
        payload={"summary": summary},
    )
    reduce_state(workspace)
    return event


def create_handoff(workspace: TrailWorkspace, *, label: str) -> dict[str, Path]:
    state = load_state(workspace)
    slug = label.replace(" ", "-").lower()
    timestamp = utc_now().replace(":", "-")
    json_path = workspace.handoffs_dir / f"{timestamp}_{slug}.json"
    md_path = workspace.handoffs_dir / f"{timestamp}_{slug}.md"
    payload = {
        "label": label,
        "created_at": utc_now(),
        "state": state,
    }
    workspace.write_json(json_path, payload)

    blockers = state.get("open_blockers") or []
    failures = state.get("recent_failures") or []
    decisions = state.get("recent_decisions") or []
    docs = state.get("docs") or []
    specs = state.get("specs") or []
    lines = [
        "# Trail Handoff",
        "",
        f"- Generated: {state.get('generated_at')}",
        f"- Goal: {state.get('current_goal') or 'No active goal recorded.'}",
        f"- Active session: {state.get('active_session') or 'none'}",
        f"- Next step: {state.get('next_step') or 'No next step recorded.'}",
        "",
        "## Open Blockers",
    ]
    lines.extend(f"- {item.get('summary') or item.get('id')}" for item in blockers) if blockers else lines.append("- None")
    lines.extend(["", "## Recent Failures"])
    lines.extend(f"- `{item.get('command')}`: {item.get('error_signature')}" for item in failures) if failures else lines.append("- None")
    lines.extend(["", "## Recent Decisions"])
    lines.extend(f"- {item.get('summary')}" for item in decisions) if decisions else lines.append("- None")
    lines.extend(["", "## Docs"])
    if docs or specs:
        for item in [*docs, *specs]:
            facts = item.get("facts") or []
            summary = "; ".join(facts[:2]) if facts else "No facts captured."
            lines.append(f"- {item.get('topic') or item.get('source')}: {summary}")
    else:
        lines.append("- None")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    emit_event(
        workspace,
        session_id=state.get("active_session") or current_session_id(workspace),
        kind="handoff_created",
        payload={"label": label, "json_path": str(json_path), "md_path": str(md_path)},
    )
    reduce_state(workspace)
    return {"json_path": json_path, "md_path": md_path}


def search_knowledge(
    workspace: TrailWorkspace,
    *,
    query: str,
    skill_name: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    state = load_state(workspace)
    query_terms = [term.lower() for term in query.split() if term.strip()]
    items: list[dict[str, Any]] = []

    for collection_name in ("docs", "specs"):
        for item in state.get(collection_name) or []:
            haystacks = [
                (item.get("topic") or "").lower(),
                (item.get("source") or "").lower(),
                " ".join(item.get("facts") or []).lower(),
            ]
            score = sum(1 for term in query_terms if any(term in hay for hay in haystacks))
            if score:
                items.append(
                    {
                        "id": f"{collection_name}:{item.get('topic') or item.get('source')}",
                        "topic": item.get("topic"),
                        "facts": item.get("facts") or [],
                        "source": {"path": item.get("source")},
                        "score": score,
                    }
                )

    if skill_name:
        skill = resolve_skill(skill_name)
        support_files = [skill.path, *[path for path in skill.path.parent.rglob("*") if path.is_file()]]
        for path in support_files[:20]:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lower_text = text.lower()
            score = sum(1 for term in query_terms if term in lower_text)
            if not score:
                continue
            snippet = text[:400].strip()
            items.append(
                {
                    "id": f"file:{path}",
                    "topic": path.name,
                    "facts": [snippet],
                    "source": {"path": str(path)},
                    "score": score,
                }
            )

    items.sort(key=lambda item: item.get("score", 0), reverse=True)
    return items[: max(1, min(limit, 20))]
