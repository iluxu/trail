from __future__ import annotations

from typing import Any

from .events import utc_now
from .workspace import TrailWorkspace


def load_defaults(workspace: TrailWorkspace) -> dict[str, Any]:
    payload = workspace.read_json(workspace.defaults_path)
    return payload if isinstance(payload, dict) else {}


def save_defaults(workspace: TrailWorkspace, **fields: Any) -> dict[str, Any]:
    current = load_defaults(workspace)
    updated = {
        **current,
        **{key: value for key, value in fields.items() if value is not None},
        "updated_at": utc_now(),
    }
    workspace.write_json(workspace.defaults_path, updated)
    return updated


def active_skill_name(workspace: TrailWorkspace) -> str | None:
    defaults = load_defaults(workspace)
    skill_name = defaults.get("active_skill")
    if isinstance(skill_name, str) and skill_name.strip():
        return skill_name
    from .migration import load_migration_pack

    migration = load_migration_pack(workspace) or {}
    skill_name = migration.get("skill_name")
    if isinstance(skill_name, str) and skill_name.strip():
        return skill_name
    return None


def active_agent_name(workspace: TrailWorkspace) -> str | None:
    defaults = load_defaults(workspace)
    agent_name = defaults.get("active_agent")
    if isinstance(agent_name, str) and agent_name.strip():
        return agent_name
    from .migration import load_migration_pack

    migration = load_migration_pack(workspace) or {}
    agent_name = migration.get("agent_name")
    if isinstance(agent_name, str) and agent_name.strip():
        return agent_name
    return None


def active_mode(workspace: TrailWorkspace) -> str | None:
    defaults = load_defaults(workspace)
    mode = defaults.get("mode")
    if isinstance(mode, str) and mode.strip():
        return mode
    from .migration import load_migration_pack

    migration = load_migration_pack(workspace)
    if migration:
        return "migration_audit"
    return None


def active_packs(workspace: TrailWorkspace) -> list[str]:
    defaults = load_defaults(workspace)
    items = defaults.get("active_packs")
    if not isinstance(items, list):
        return []
    return [str(item) for item in items if str(item).strip()]
