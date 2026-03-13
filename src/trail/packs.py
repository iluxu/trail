from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .defaults import active_packs, save_defaults
from .events import utc_now
from .workspace import TrailWorkspace


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "unnamed"


def pack_path(workspace: TrailWorkspace, slug: str) -> Path:
    return workspace.packs_dir / f"{_slugify(slug)}.json"


def load_pack(workspace: TrailWorkspace, slug: str) -> dict[str, Any] | None:
    path = pack_path(workspace, slug)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_pack(workspace: TrailWorkspace, payload: dict[str, Any]) -> dict[str, Any]:
    slug = _slugify(str(payload.get("slug") or payload.get("title") or "pack"))
    record = {
        "slug": slug,
        "title": payload.get("title") or slug,
        "kind": payload.get("kind") or "knowledge",
        "summary": payload.get("summary") or "",
        "sources": payload.get("sources") or [],
        "facts": payload.get("facts") or [],
        "directives": payload.get("directives") or [],
        "owners": payload.get("owners") or [],
        "status": payload.get("status") or "active",
        "created_at": payload.get("created_at") or utc_now(),
        "updated_at": utc_now(),
    }
    workspace.write_json(pack_path(workspace, slug), record)
    return record


def list_packs(workspace: TrailWorkspace) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(workspace.packs_dir.glob("*.json")):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return items


def activate_pack(workspace: TrailWorkspace, slug: str) -> list[str]:
    current = active_packs(workspace)
    normalized = _slugify(slug)
    updated = sorted({*current, normalized})
    save_defaults(workspace, active_packs=updated)
    return updated


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


def _extract_facts(path: Path) -> list[str]:
    facts: list[str] = []
    current_heading = path.stem.replace("_", " ").strip()
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        heading = _extract_heading(raw_line)
        if heading:
            current_heading = heading
            continue
        bullet = _extract_bullet(raw_line)
        if not bullet:
            continue
        fact = f"{current_heading}: {bullet}" if current_heading else bullet
        if fact in seen:
            continue
        seen.add(fact)
        facts.append(fact)
    return facts


def import_pack_from_files(
    workspace: TrailWorkspace,
    *,
    slug: str,
    title: str,
    kind: str,
    files: list[str],
    summary: str | None = None,
    activate: bool = False,
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    facts: list[str] = []
    directives: list[str] = []
    seen: set[str] = set()
    for raw in files:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Pack source not found: {raw}")
        file_facts = _extract_facts(path)
        for fact in file_facts:
            if fact in seen:
                continue
            seen.add(fact)
            facts.append(fact)
        directives.extend(file_facts[:5])
        sources.append({"path": str(path), "facts_count": len(file_facts)})

    record = save_pack(
        workspace,
        {
            "slug": slug,
            "title": title,
            "kind": kind,
            "summary": summary or f"{title} pack built from {len(files)} source files.",
            "sources": sources,
            "facts": facts,
            "directives": directives[:12],
        },
    )
    if activate:
        activate_pack(workspace, record["slug"])
    return record
