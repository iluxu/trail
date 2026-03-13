from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .skills import collect_skill_support_files, resolve_skill


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "unnamed"


def skill_record_id(slug: str) -> str:
    return f"skill_{slug.replace('-', '_')}"


def project_record_id(slug: str) -> str:
    return f"proj_{slug.replace('-', '_')}"


def conversation_record_id(identifier: str) -> str:
    if identifier.startswith("conv_"):
        return identifier
    return f"conv_{slugify(identifier).replace('-', '_')}"


def agent_record_id(slug: str) -> str:
    return f"agent_{slug.replace('-', '_')}"


@dataclass(frozen=True)
class GlobalRegistry:
    root: Path

    @property
    def skills_dir(self) -> Path:
        return self.root / "skills"

    @property
    def skill_objects_dir(self) -> Path:
        return self.skills_dir / "objects"

    @property
    def skill_registry_path(self) -> Path:
        return self.skills_dir / "registry.json"

    @property
    def projects_dir(self) -> Path:
        return self.root / "projects"

    @property
    def project_objects_dir(self) -> Path:
        return self.projects_dir / "objects"

    @property
    def project_registry_path(self) -> Path:
        return self.projects_dir / "registry.json"

    @property
    def conversations_dir(self) -> Path:
        return self.root / "conversations"

    @property
    def conversation_objects_dir(self) -> Path:
        return self.conversations_dir / "objects"

    @property
    def conversation_registry_path(self) -> Path:
        return self.conversations_dir / "registry.json"

    @property
    def agents_dir(self) -> Path:
        return self.root / "agents"

    @property
    def agent_objects_dir(self) -> Path:
        return self.agents_dir / "objects"

    @property
    def agent_registry_path(self) -> Path:
        return self.agents_dir / "registry.json"

    def ensure(self) -> None:
        self.skill_objects_dir.mkdir(parents=True, exist_ok=True)
        self.project_objects_dir.mkdir(parents=True, exist_ok=True)
        self.conversation_objects_dir.mkdir(parents=True, exist_ok=True)
        self.agent_objects_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_registry_file(self.skill_registry_path)
        self._ensure_registry_file(self.project_registry_path)
        self._ensure_registry_file(self.conversation_registry_path)
        self._ensure_registry_file(self.agent_registry_path)

    def _ensure_registry_file(self, path: Path) -> None:
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"items": []}, indent=2) + "\n", encoding="utf-8")

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _registry_items(self, path: Path) -> list[str]:
        payload = self._read_json(path)
        items = payload.get("items")
        return items if isinstance(items, list) else []

    def _set_registry_items(self, path: Path, items: list[str]) -> None:
        unique = sorted({item for item in items if item})
        self._write_json(path, {"items": unique})

    def _upsert_object(self, registry_path: Path, objects_dir: Path, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure()
        self._write_json(objects_dir / f"{record_id}.json", payload)
        items = self._registry_items(registry_path)
        if record_id not in items:
            items.append(record_id)
            self._set_registry_items(registry_path, items)
        return payload

    def list_skills(self) -> list[dict[str, Any]]:
        self.ensure()
        records: list[dict[str, Any]] = []
        for record_id in self._registry_items(self.skill_registry_path):
            path = self.skill_objects_dir / f"{record_id}.json"
            if path.exists():
                records.append(self._read_json(path))
        return records

    def list_projects(self) -> list[dict[str, Any]]:
        self.ensure()
        records: list[dict[str, Any]] = []
        for record_id in self._registry_items(self.project_registry_path):
            path = self.project_objects_dir / f"{record_id}.json"
            if path.exists():
                records.append(self._read_json(path))
        return records

    def list_conversations(self) -> list[dict[str, Any]]:
        self.ensure()
        records: list[dict[str, Any]] = []
        for record_id in self._registry_items(self.conversation_registry_path):
            path = self.conversation_objects_dir / f"{record_id}.json"
            if path.exists():
                records.append(self._read_json(path))
        return records

    def list_agents(self) -> list[dict[str, Any]]:
        self.ensure()
        records: list[dict[str, Any]] = []
        for record_id in self._registry_items(self.agent_registry_path):
            path = self.agent_objects_dir / f"{record_id}.json"
            if path.exists():
                records.append(self._read_json(path))
        return records

    def get_skill(self, identifier: str) -> dict[str, Any] | None:
        self.ensure()
        target = slugify(identifier)
        for record in self.list_skills():
            if record.get("id") == identifier or record.get("slug") == target:
                return record
        return None

    def get_project(self, identifier: str) -> dict[str, Any] | None:
        self.ensure()
        target = slugify(identifier)
        resolved = str(Path(identifier).expanduser().resolve()) if identifier.startswith("/") or identifier.startswith("~") else None
        for record in self.list_projects():
            if record.get("id") == identifier or record.get("slug") == target:
                return record
            if resolved and record.get("root") == resolved:
                return record
        return None

    def get_project_by_root(self, root: Path) -> dict[str, Any] | None:
        resolved = str(root.resolve())
        for record in self.list_projects():
            if record.get("root") == resolved:
                return record
        return None

    def get_conversation(self, identifier: str) -> dict[str, Any] | None:
        self.ensure()
        target = conversation_record_id(identifier)
        for record in self.list_conversations():
            if record.get("id") == identifier or record.get("id") == target:
                return record
            if record.get("session_id") == identifier:
                return record
        return None

    def get_agent(self, identifier: str) -> dict[str, Any] | None:
        self.ensure()
        target = slugify(identifier)
        for record in self.list_agents():
            if record.get("id") == identifier or record.get("slug") == target:
                return record
        return None

    def upsert_skill(self, name_or_path: str) -> dict[str, Any]:
        skill = resolve_skill(name_or_path)
        slug = slugify(skill.name)
        record_id = skill_record_id(slug)
        existing = self.get_skill(slug) or {}
        support_files = [str(path) for path in collect_skill_support_files(skill)[:50]]
        payload = {
            "id": record_id,
            "slug": slug,
            "title": skill.name,
            "description": skill.description,
            "source": {"kind": "local_codex_skill", "path": str(skill.path)},
            "support_files": support_files,
            "linked_projects": existing.get("linked_projects") or [],
            "linked_conversations": existing.get("linked_conversations") or [],
            "linked_knowledge": existing.get("linked_knowledge") or [],
            "tags": existing.get("tags") or [],
            "status": existing.get("status") or "active",
        }
        return self._upsert_object(self.skill_registry_path, self.skill_objects_dir, record_id, payload)

    def upsert_project(self, root: Path, *, title: str | None = None, slug: str | None = None) -> dict[str, Any]:
        resolved_root = root.resolve()
        existing = self.get_project_by_root(resolved_root) or {}
        project_slug = slugify(slug or resolved_root.name)
        record_id = project_record_id(project_slug)
        payload = {
            "id": record_id,
            "slug": project_slug,
            "title": title or existing.get("title") or resolved_root.name,
            "root": str(resolved_root),
            "repo": {
                "git": (resolved_root / ".git").exists(),
                "remote": existing.get("repo", {}).get("remote") if isinstance(existing.get("repo"), dict) else None,
                "default_branch": existing.get("repo", {}).get("default_branch") if isinstance(existing.get("repo"), dict) else "main",
            },
            "status": existing.get("status") or "active",
            "goals": existing.get("goals") or [],
            "linked_skills": existing.get("linked_skills") or [],
            "linked_conversations": existing.get("linked_conversations") or [],
            "owners": existing.get("owners") or [],
            "tags": existing.get("tags") or [],
        }
        return self._upsert_object(self.project_registry_path, self.project_objects_dir, record_id, payload)

    def link_skill_project(self, skill_identifier: str, project_identifier: str) -> tuple[dict[str, Any], dict[str, Any]]:
        skill = self.get_skill(skill_identifier)
        if not skill:
            skill = self.upsert_skill(skill_identifier)

        project = self.get_project(project_identifier)
        if not project:
            project_path = Path(project_identifier).expanduser()
            if project_path.exists():
                project = self.upsert_project(project_path)
            else:
                raise FileNotFoundError(f"Unknown project: {project_identifier}")

        skill_projects = set(skill.get("linked_projects") or [])
        skill_projects.add(project["id"])
        skill["linked_projects"] = sorted(skill_projects)

        project_skills = set(project.get("linked_skills") or [])
        project_skills.add(skill["id"])
        project["linked_skills"] = sorted(project_skills)

        self._upsert_object(self.skill_registry_path, self.skill_objects_dir, skill["id"], skill)
        self._upsert_object(self.project_registry_path, self.project_objects_dir, project["id"], project)
        return skill, project

    def upsert_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure()
        conversation_id = conversation_record_id(str(payload.get("id") or payload.get("session_id") or "conversation"))
        existing = self.get_conversation(conversation_id) or {}

        project_id = payload.get("project_id")
        skill_ids = list(payload.get("skill_ids") or existing.get("skill_ids") or [])

        record = {
            "id": conversation_id,
            "session_id": payload.get("session_id") or existing.get("session_id"),
            "project_id": project_id or existing.get("project_id"),
            "skill_ids": skill_ids,
            "title": payload.get("title") or existing.get("title") or conversation_id,
            "status": payload.get("status") or existing.get("status") or "open",
            "started_at": payload.get("started_at") or existing.get("started_at"),
            "updated_at": payload.get("updated_at") or existing.get("updated_at"),
            "current_goal": payload.get("current_goal") or existing.get("current_goal"),
            "summary": payload.get("summary") or existing.get("summary"),
            "next_step": payload.get("next_step") or existing.get("next_step"),
            "blockers": payload.get("blockers") or existing.get("blockers") or [],
            "transcript_ref": payload.get("transcript_ref") or existing.get("transcript_ref"),
            "handoff_refs": payload.get("handoff_refs") or existing.get("handoff_refs") or [],
            "tags": payload.get("tags") or existing.get("tags") or [],
            "root": payload.get("root") or existing.get("root"),
        }

        record = self._upsert_object(self.conversation_registry_path, self.conversation_objects_dir, conversation_id, record)

        if record.get("project_id"):
            project = self.get_project(record["project_id"])
            if project:
                linked = set(project.get("linked_conversations") or [])
                linked.add(record["id"])
                project["linked_conversations"] = sorted(linked)
                self._upsert_object(self.project_registry_path, self.project_objects_dir, project["id"], project)

        for skill_id in record.get("skill_ids") or []:
            skill = self.get_skill(skill_id)
            if skill:
                linked = set(skill.get("linked_conversations") or [])
                linked.add(record["id"])
                skill["linked_conversations"] = sorted(linked)
                self._upsert_object(self.skill_registry_path, self.skill_objects_dir, skill["id"], skill)

        return record

    def upsert_agent(
        self,
        *,
        name: str,
        role: str | None = None,
        description: str | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        slug = slugify(name)
        record_id = agent_record_id(slug)
        existing = self.get_agent(slug) or {}
        payload = {
            "id": record_id,
            "slug": slug,
            "title": name,
            "role": role or existing.get("role") or "specialist",
            "description": description or existing.get("description") or "",
            "system_prompt": system_prompt or existing.get("system_prompt") or "",
            "linked_projects": existing.get("linked_projects") or [],
            "linked_skills": existing.get("linked_skills") or [],
            "linked_conversations": existing.get("linked_conversations") or [],
            "linked_knowledge": existing.get("linked_knowledge") or [],
            "tags": existing.get("tags") or [],
            "status": existing.get("status") or "active",
        }
        return self._upsert_object(self.agent_registry_path, self.agent_objects_dir, record_id, payload)

    def link_agent(
        self,
        agent_identifier: str,
        *,
        project_identifier: str | None = None,
        skill_identifier: str | None = None,
        conversation_identifier: str | None = None,
    ) -> dict[str, Any]:
        agent = self.get_agent(agent_identifier)
        if not agent:
            agent = self.upsert_agent(name=agent_identifier)

        if project_identifier:
            project = self.get_project(project_identifier)
            if not project:
                project_path = Path(project_identifier).expanduser()
                if project_path.exists():
                    project = self.upsert_project(project_path)
                else:
                    raise FileNotFoundError(f"Unknown project: {project_identifier}")
            linked = set(agent.get("linked_projects") or [])
            linked.add(project["id"])
            agent["linked_projects"] = sorted(linked)

        if skill_identifier:
            skill = self.get_skill(skill_identifier)
            if not skill:
                skill = self.upsert_skill(skill_identifier)
            linked = set(agent.get("linked_skills") or [])
            linked.add(skill["id"])
            agent["linked_skills"] = sorted(linked)

        if conversation_identifier:
            conversation = self.get_conversation(conversation_identifier)
            if not conversation:
                raise FileNotFoundError(f"Unknown conversation: {conversation_identifier}")
            linked = set(agent.get("linked_conversations") or [])
            linked.add(conversation["id"])
            agent["linked_conversations"] = sorted(linked)

        return self._upsert_object(self.agent_registry_path, self.agent_objects_dir, agent["id"], agent)


def global_registry() -> GlobalRegistry:
    registry = GlobalRegistry(root=Path.home() / ".trail")
    registry.ensure()
    return registry
