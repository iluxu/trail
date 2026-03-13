from __future__ import annotations

from collections import Counter
from typing import Any

from .events import read_events, utc_now
from .workspace import TrailWorkspace


def _trim_items(items: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    if len(items) <= limit:
        return items
    return items[-limit:]


def reduce_state(workspace: TrailWorkspace) -> dict[str, Any]:
    events = read_events(workspace)
    open_blockers: dict[str, dict[str, Any]] = {}
    decisions: list[dict[str, Any]] = []
    recent_failures: list[dict[str, Any]] = []
    docs: dict[str, dict[str, Any]] = {}
    specs: dict[str, dict[str, Any]] = {}
    sessions: list[str] = []
    last_command: dict[str, Any] | None = None
    next_step: str | None = None
    current_goal: str | None = None
    active_session: str | None = None
    event_counts: Counter[str] = Counter()

    for event in events:
        kind = event["kind"]
        payload = event.get("payload") or {}
        session_id = event.get("session_id")
        event_counts[kind] += 1

        if session_id and session_id not in sessions:
            sessions.append(session_id)

        if kind in {"session_started", "session_resumed"}:
            active_session = session_id
        elif kind == "session_finished" and active_session == session_id:
            active_session = None
        elif kind == "goal_set":
            current_goal = payload.get("goal") or current_goal
        elif kind == "command_run":
            last_command = {
                "command": payload.get("command"),
                "started_at": event.get("ts"),
            }
        elif kind == "command_failed":
            recent_failures.append(
                {
                    "command": payload.get("command"),
                    "exit_code": payload.get("exit_code"),
                    "error_signature": payload.get("error_signature"),
                    "notes": payload.get("notes"),
                    "ts": event.get("ts"),
                }
            )
        elif kind == "decision_made":
            decisions.append(
                {
                    "summary": payload.get("summary"),
                    "reason": payload.get("reason"),
                    "impact": payload.get("impact"),
                    "ts": event.get("ts"),
                }
            )
        elif kind == "blocker_opened":
            blocker_id = payload.get("id") or f"blocker:{len(open_blockers) + 1}"
            open_blockers[blocker_id] = {
                "id": blocker_id,
                "summary": payload.get("summary"),
                "severity": payload.get("severity"),
                "owner": payload.get("owner"),
                "workaround": payload.get("workaround"),
                "ts": event.get("ts"),
            }
        elif kind == "blocker_resolved":
            blocker_id = payload.get("id")
            if blocker_id:
                open_blockers.pop(blocker_id, None)
        elif kind == "doc_learned":
            doc = {
                "source": payload.get("source"),
                "topic": payload.get("topic"),
                "facts": payload.get("facts") or [],
                "ts": event.get("ts"),
            }
            key = f"{doc.get('source')}::{doc.get('topic')}"
            docs[key] = doc
        elif kind == "spec_learned":
            spec = {
                "source": payload.get("source"),
                "topic": payload.get("topic"),
                "facts": payload.get("facts") or [],
                "ts": event.get("ts"),
            }
            key = f"{spec.get('source')}::{spec.get('topic')}"
            specs[key] = spec
        elif kind == "next_step_set":
            next_step = payload.get("summary") or next_step

    state: dict[str, Any] = {
        "generated_at": utc_now(),
        "project_root": str(workspace.root),
        "active_session": active_session,
        "session_count": len(sessions),
        "event_count": len(events),
        "current_goal": current_goal,
        "next_step": next_step,
        "last_command": last_command,
        "open_blockers": list(open_blockers.values()),
        "recent_failures": _trim_items(recent_failures),
        "recent_decisions": _trim_items(decisions),
        "docs": _trim_items(list(docs.values())),
        "specs": _trim_items(list(specs.values())),
        "event_counts": dict(event_counts),
    }
    workspace.write_json(workspace.current_state_path, state)
    workspace.write_json(workspace.state_dir / "blockers.json", {"items": state["open_blockers"]})
    workspace.write_json(workspace.state_dir / "decisions.json", {"items": state["recent_decisions"]})
    workspace.write_json(workspace.state_dir / "docs.json", {"items": state["docs"], "specs": state["specs"]})
    return state
