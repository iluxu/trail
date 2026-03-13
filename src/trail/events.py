from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .workspace import TrailWorkspace


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def emit_event(
    workspace: TrailWorkspace,
    *,
    session_id: str,
    kind: str,
    payload: dict[str, Any] | None = None,
    scope: str = "repo",
    certainty: str = "fact",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "ts": utc_now(),
        "session_id": session_id,
        "kind": kind,
        "scope": scope,
        "certainty": certainty,
        "tags": tags or [],
        "payload": payload or {},
    }
    with workspace.events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def read_events(workspace: TrailWorkspace) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not workspace.events_path.exists():
        return events
    with workspace.events_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events
