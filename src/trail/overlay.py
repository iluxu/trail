from __future__ import annotations

from typing import Any

from .defaults import active_packs
from .packs import load_pack
from .workspace import TrailWorkspace


def overlay_path(workspace: TrailWorkspace, skill_name: str) -> str:
    return str(workspace.skills_overlays_dir / f"{skill_name}.json")


def load_skill_overlay(workspace: TrailWorkspace, skill_name: str) -> dict[str, Any]:
    path = workspace.skills_overlays_dir / f"{skill_name}.json"
    payload = workspace.read_json(path)
    if payload:
        return payload
    return {
        "skill": skill_name,
        "project_summary": "",
        "current_focus": "",
        "directives": [],
        "avoid": [],
        "pack_slugs": [],
    }


def save_skill_overlay(
    workspace: TrailWorkspace,
    *,
    skill_name: str,
    project_summary: str | None = None,
    current_focus: str | None = None,
    directives: list[str] | None = None,
    avoid: list[str] | None = None,
    pack_slugs: list[str] | None = None,
) -> dict[str, Any]:
    current = load_skill_overlay(workspace, skill_name)
    merged = {
        **current,
        "skill": skill_name,
        "project_summary": project_summary if project_summary is not None else current.get("project_summary") or "",
        "current_focus": current_focus if current_focus is not None else current.get("current_focus") or "",
        "directives": sorted({*(current.get("directives") or []), *((directives or []))}),
        "avoid": sorted({*(current.get("avoid") or []), *((avoid or []))}),
        "pack_slugs": sorted({*(current.get("pack_slugs") or []), *((pack_slugs or []))}),
    }
    workspace.write_json(workspace.skills_overlays_dir / f"{skill_name}.json", merged)
    return merged


def build_skill_overlay(workspace: TrailWorkspace, skill_name: str, *, state: dict[str, Any]) -> dict[str, Any]:
    overlay = load_skill_overlay(workspace, skill_name)
    pack_slugs = sorted({*(overlay.get("pack_slugs") or []), *active_packs(workspace)})
    packs = [pack for slug in pack_slugs if (pack := load_pack(workspace, slug))]
    dynamic_directives = [directive for pack in packs for directive in (pack.get("directives") or [])[:4]]
    recent_failures = [item.get("error_signature") for item in (state.get("recent_failures") or []) if item.get("error_signature")]
    recent_decisions = [item.get("summary") for item in (state.get("recent_decisions") or []) if item.get("summary")]
    return {
        "skill": skill_name,
        "project_summary": overlay.get("project_summary") or "",
        "current_focus": overlay.get("current_focus") or state.get("next_step") or "",
        "directives": [*dict.fromkeys([*(overlay.get("directives") or []), *dynamic_directives])],
        "avoid": [*dict.fromkeys(overlay.get("avoid") or [])],
        "pack_slugs": pack_slugs,
        "packs": packs,
        "recent_failures": recent_failures[:5],
        "recent_decisions": recent_decisions[:5],
    }
