from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .workspace import TrailWorkspace


DEFAULT_SKILLS_DIR = Path.home() / ".codex" / "skills"


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    description: str
    body: str
    frontmatter: dict[str, str]


def trail_usage_guidance() -> list[str]:
    return [
        "Trail Usage:",
        "- At the start, call Trail to fetch current context before making project-state assumptions.",
        "- Before deep skill work, call Trail to fetch skill context if it is available.",
        "- Before answering from memory about docs or specs, call Trail to search retained knowledge.",
        "- After an important decision, record it in Trail.",
        "- When you discover a blocker, record it in Trail.",
        "- Before ending or parking the task, save a Trail handoff.",
    ]


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---\n"):
        return {}, raw
    parts = raw.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, raw
    header, body = parts
    frontmatter: dict[str, str] = {}
    for line in header.splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return frontmatter, body.strip()


def resolve_skill(name_or_path: str) -> Skill:
    candidate = Path(name_or_path).expanduser()
    if candidate.exists():
        skill_path = candidate
    else:
        skill_path = DEFAULT_SKILLS_DIR / name_or_path / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {name_or_path}")

    raw = skill_path.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(raw)
    name = frontmatter.get("name") or skill_path.parent.name
    description = frontmatter.get("description") or ""
    return Skill(
        name=name,
        path=skill_path,
        description=description,
        body=body,
        frontmatter=frontmatter,
    )


def collect_skill_support_files(skill: Skill) -> list[Path]:
    files: list[Path] = []
    for subdir in ("references", "scripts", "assets", "templates"):
        base = skill.path.parent / subdir
        if not base.exists():
            continue
        for item in sorted(base.rglob("*")):
            if item.is_file():
                files.append(item)
    return files


def build_skill_briefing(workspace: TrailWorkspace, skill: Skill, state: dict, user_task: str | None) -> str:
    blockers = state.get("open_blockers") or []
    decisions = state.get("recent_decisions") or []
    failures = state.get("recent_failures") or []
    docs = state.get("docs") or []
    specs = state.get("specs") or []
    support_files = collect_skill_support_files(skill)

    lines = [
        f"You are operating with the Codex skill `{skill.name}`.",
        "",
        "Trail context:",
        f"- Project root: {workspace.root}",
        f"- Active goal: {state.get('current_goal') or 'No active goal recorded.'}",
        f"- Next step: {state.get('next_step') or 'No next step recorded.'}",
        f"- Open blockers: {len(blockers)}",
        f"- Recent failures: {len(failures)}",
        f"- Skill file: {skill.path}",
    ]

    if decisions:
        lines.append("- Recent decisions:")
        for item in decisions[-5:]:
            if item.get("summary"):
                lines.append(f"  - {item['summary']}")

    if blockers:
        lines.append("- Open blockers detail:")
        for item in blockers[-5:]:
            lines.append(f"  - {item.get('summary') or item.get('id')}")

    if failures:
        lines.append("- Recent failures detail:")
        for item in failures[-5:]:
            lines.append(f"  - {item.get('command')}: {item.get('error_signature')}")

    knowledge_items = [*docs[-3:], *specs[-3:]]
    if knowledge_items:
        lines.append("- Relevant retained facts:")
        for item in knowledge_items:
            facts = item.get("facts") or []
            summary = "; ".join(facts[:2]) if facts else "No facts captured."
            lines.append(f"  - {item.get('topic') or item.get('source')}: {summary}")

    if support_files:
        lines.append("- Skill support files:")
        for path in support_files[:12]:
            lines.append(f"  - {path}")

    lines.extend(
        [
            "",
            *trail_usage_guidance(),
            "",
            "Skill instructions:",
            skill.body.strip(),
        ]
    )

    if user_task:
        lines.extend(
            [
                "",
                "User task:",
                user_task.strip(),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "User task:",
                "Start by confirming the exact goal and pick the correct skill mode before taking action.",
            ]
        )

    return "\n".join(lines).strip() + "\n"
