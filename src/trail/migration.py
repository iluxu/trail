from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .events import emit_event, utc_now
from .registry import global_registry
from .workspace import TrailWorkspace


DEFAULT_AGENT_NAME = "migration-auditor"


def _migration_dir(workspace: TrailWorkspace) -> Path:
    return workspace.trail_dir / "audits" / "migration"


def migration_config_path(workspace: TrailWorkspace) -> Path:
    return _migration_dir(workspace) / "config.json"


def migration_checklist_path(workspace: TrailWorkspace) -> Path:
    return _migration_dir(workspace) / "checklist.json"


def migration_report_template_path(workspace: TrailWorkspace) -> Path:
    return _migration_dir(workspace) / "report_template.md"


def load_migration_pack(workspace: TrailWorkspace) -> dict[str, Any] | None:
    path = migration_config_path(workspace)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_source(path_value: str, *, base_dir: Path) -> Path:
    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Migration source not found: {path_value}")
    return candidate


def _extract_heading(line: str) -> str | None:
    match = re.match(r"^\s{0,3}(#+)\s+(.*)$", line)
    if not match:
        return None
    return match.group(2).strip()


def _extract_bullet(line: str) -> str | None:
    match = re.match(r"^\s*[-*]\s+(.*)$", line)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).strip())


def extract_markdown_items(path: Path) -> list[dict[str, str]]:
    title = path.stem.replace("_", " ").strip()
    current_heading = title
    items: list[dict[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        heading = _extract_heading(raw_line)
        if heading:
            current_heading = heading
            continue
        bullet = _extract_bullet(raw_line)
        if not bullet:
            continue
        items.append({"section": current_heading, "text": bullet})
    return items


def _dedupe_facts(items: list[dict[str, str]]) -> list[str]:
    facts: list[str] = []
    seen: set[str] = set()
    for item in items:
        section = item["section"].strip()
        text = item["text"].strip()
        fact = f"{section}: {text}" if section else text
        if fact in seen:
            continue
        seen.add(fact)
        facts.append(fact)
    return facts


def _write_report_template(workspace: TrailWorkspace, config: dict[str, Any], checklist: dict[str, Any]) -> None:
    lines = [
        "# Migration Audit Report",
        "",
        f"- Generated: {utc_now()}",
        f"- Project root: {workspace.root}",
        f"- Skill: {config.get('skill_name') or 'none'}",
        f"- Agent: {config.get('agent_name')}",
        "",
        "## Executive Summary",
        "",
        "- Overall status: ",
        "- Critical gaps: ",
        "- Business-risk areas: ",
        "- Recommended next step: ",
        "",
        "## Status Legend",
        "",
        "- `COMPLIANT`: verified and aligned",
        "- `GAP`: missing, incorrect, or regressed",
        "- `NEEDS_VERIFICATION`: unclear without runtime/manual confirmation",
        "- `NOT_APPLICABLE`: not expected in this scope",
        "",
    ]
    for category in checklist.get("categories") or []:
        lines.extend([f"## {category['title']}", ""])
        for item in category.get("items") or []:
            lines.append(f"- [ ] {item['section']}: {item['text']} | Status: ")
        lines.append("")
    migration_report_template_path(workspace).write_text("\n".join(lines), encoding="utf-8")


def _agent_prompt(skill_name: str | None) -> str:
    focus = (
        f"Use the linked skill `{skill_name}` for repo-specific workflow and conventions. "
        if skill_name
        else ""
    )
    return (
        "Act as the migration audit lead for this project. "
        "Compare legacy business behavior against the migrated implementation point by point. "
        "Check EUI21/ECL21 visible conventions separately from business correctness. "
        "Classify findings as COMPLIANT, GAP, NEEDS_VERIFICATION, or NOT_APPLICABLE. "
        "Prioritize high-risk flows, cite the relevant source document when making claims, "
        "and record important findings back into Trail as decisions, blockers, and next steps. "
        f"{focus}"
        "Do not assume a migration is complete just because the UI looks migrated."
    )


def setup_migration_pack(
    workspace: TrailWorkspace,
    *,
    business_rules: str,
    conventions: str,
    gaps: str,
    flows: str,
    skill_name: str | None = None,
    agent_name: str = DEFAULT_AGENT_NAME,
) -> dict[str, Any]:
    registry = global_registry()
    project = registry.upsert_project(workspace.root)

    skill = None
    warnings: list[str] = []
    if skill_name:
        try:
            skill = registry.upsert_skill(skill_name)
            skill, project = registry.link_skill_project(skill_name, project["slug"])
        except FileNotFoundError:
            warnings.append(f"Skill not found and was not linked: {skill_name}")

    agent = registry.upsert_agent(
        name=agent_name,
        role="migration_auditor",
        description="Specialist agent for legacy-to-migrated business rule and EUI21/ECL21 audits",
        system_prompt=_agent_prompt(skill["slug"] if skill else None),
    )
    agent = registry.link_agent(
        agent["slug"],
        project_identifier=project["slug"],
        skill_identifier=skill["slug"] if skill else None,
    )

    sources = [
        ("business_rules", "Business Rules", business_rules, "spec_learned"),
        ("eui21_ecl21_conventions", "EUI21 / ECL21 Conventions", conventions, "spec_learned"),
        ("migration_gaps", "Migration Gaps", gaps, "doc_learned"),
        ("critical_flows", "Critical Flows", flows, "doc_learned"),
    ]

    knowledge_entries: list[dict[str, Any]] = []
    categories: list[dict[str, Any]] = []
    for slug, title, raw_path, event_kind in sources:
        resolved = _resolve_source(raw_path, base_dir=Path.cwd())
        items = extract_markdown_items(resolved)
        facts = _dedupe_facts(items)
        emit_event(
            workspace,
            session_id="manual",
            kind=event_kind,
            payload={"source": str(resolved), "topic": title, "facts": facts},
        )
        knowledge_entries.append(
            {
                "slug": slug,
                "title": title,
                "path": str(resolved),
                "facts_count": len(facts),
            }
        )
        categories.append(
            {
                "slug": slug,
                "title": title,
                "source": str(resolved),
                "items": items,
            }
        )

    config = {
        "kind": "migration_audit",
        "created_at": utc_now(),
        "project_id": project["id"],
        "project_slug": project["slug"],
        "project_root": str(workspace.root),
        "skill_name": skill["slug"] if skill else None,
        "agent_name": agent["slug"],
        "sources": knowledge_entries,
        "statuses": ["COMPLIANT", "GAP", "NEEDS_VERIFICATION", "NOT_APPLICABLE"],
    }
    checklist = {
        "generated_at": utc_now(),
        "project_id": project["id"],
        "categories": categories,
    }

    workspace.write_json(migration_config_path(workspace), config)
    workspace.write_json(migration_checklist_path(workspace), checklist)
    _write_report_template(workspace, config, checklist)

    return {
        "project": project,
        "skill": skill,
        "agent": agent,
        "migration_pack": config,
        "checklist_path": str(migration_checklist_path(workspace)),
        "report_template_path": str(migration_report_template_path(workspace)),
        "warnings": warnings,
    }


def build_migration_prompt(workspace: TrailWorkspace, *, user_task: str | None = None) -> str:
    config = load_migration_pack(workspace)
    if not config:
        raise FileNotFoundError("No migration pack found. Run `trail migration setup` first.")

    state = workspace.read_json(workspace.current_state_path) or {}
    checklist = workspace.read_json(migration_checklist_path(workspace)) or {}

    lines = [
        "You are operating as Trail's migration auditor.",
        "",
        "Audit goal:",
        "- Verify that legacy business rules are preserved in the migrated project.",
        "- Verify that EUI21 / ECL21 conventions are applied correctly.",
        "- Separate visible migration polish from true business correctness.",
        "",
        "Trail context:",
        f"- Project root: {workspace.root}",
        f"- Active goal: {state.get('current_goal') or 'No active goal recorded.'}",
        f"- Next step: {state.get('next_step') or 'No next step recorded.'}",
        f"- Open blockers: {len(state.get('open_blockers') or [])}",
        f"- Migration agent: {config.get('agent_name')}",
        f"- Linked skill: {config.get('skill_name') or 'none'}",
        "",
        "Source documents:",
    ]
    for source in config.get("sources") or []:
        lines.append(f"- {source['title']}: {source['path']}")

    lines.extend(
        [
            "",
            "Required method:",
            "- Start by calling Trail to fetch current context.",
            "- Use Trail knowledge search when you need rule, convention, gap, or flow details.",
            "- Audit point by point; do not stop at visual parity.",
            "- Record confirmed gaps as blockers or decisions in Trail.",
            "- End with a manager-ready summary and a precise next step.",
            "",
            "Status labels:",
            "- COMPLIANT",
            "- GAP",
            "- NEEDS_VERIFICATION",
            "- NOT_APPLICABLE",
            "",
            "Priority checklist samples:",
        ]
    )

    for category in (checklist.get("categories") or [])[:4]:
        lines.append(f"- {category['title']}:")
        for item in (category.get("items") or [])[:6]:
            lines.append(f"  - {item['section']}: {item['text']}")

    lines.extend(
        [
            "",
            "Expected output:",
            "1. Executive summary",
            "2. Critical gaps",
            "3. Needs verification",
            "4. Detailed checklist by source document",
            "5. Recommended next step",
            "",
            "Report template path:",
            str(migration_report_template_path(workspace)),
            "",
            "User task:",
            user_task or "Audit the current migrated implementation against the migration pack.",
        ]
    )
    return "\n".join(lines).strip() + "\n"
