from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


TRAIL_DIRNAME = ".trail"


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / TRAIL_DIRNAME).exists():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return current


@dataclass(frozen=True)
class TrailWorkspace:
    root: Path

    @property
    def trail_dir(self) -> Path:
        return self.root / TRAIL_DIRNAME

    @property
    def events_path(self) -> Path:
        return self.trail_dir / "events.jsonl"

    @property
    def config_path(self) -> Path:
        return self.trail_dir / "config.toml"

    @property
    def sessions_dir(self) -> Path:
        return self.trail_dir / "sessions"

    @property
    def state_dir(self) -> Path:
        return self.trail_dir / "state"

    @property
    def checkpoints_dir(self) -> Path:
        return self.trail_dir / "checkpoints"

    @property
    def handoffs_dir(self) -> Path:
        return self.trail_dir / "handoffs"

    @property
    def conversations_dir(self) -> Path:
        return self.trail_dir / "conversations"

    @property
    def context_dir(self) -> Path:
        return self.trail_dir / "context"

    @property
    def audits_dir(self) -> Path:
        return self.trail_dir / "audits"

    @property
    def skills_memory_dir(self) -> Path:
        return self.trail_dir / "skills" / "memory"

    @property
    def cache_dir(self) -> Path:
        return self.trail_dir / "cache"

    @property
    def transcripts_dir(self) -> Path:
        return self.trail_dir / "transcripts"

    @property
    def current_session_path(self) -> Path:
        return self.sessions_dir / "current.json"

    @property
    def current_state_path(self) -> Path:
        return self.state_dir / "current.json"

    @property
    def current_conversation_path(self) -> Path:
        return self.conversations_dir / "current.json"

    @property
    def current_context_path(self) -> Path:
        return self.context_dir / "current.json"

    @property
    def defaults_path(self) -> Path:
        return self.context_dir / "defaults.json"

    def ensure(self) -> None:
        self.trail_dir.mkdir(exist_ok=True)
        self.sessions_dir.mkdir(exist_ok=True)
        self.state_dir.mkdir(exist_ok=True)
        self.checkpoints_dir.mkdir(exist_ok=True)
        self.handoffs_dir.mkdir(exist_ok=True)
        self.conversations_dir.mkdir(exist_ok=True)
        self.context_dir.mkdir(exist_ok=True)
        self.audits_dir.mkdir(exist_ok=True)
        self.skills_memory_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)

        if not self.events_path.exists():
            self.events_path.touch()

        if not self.config_path.exists():
            self.config_path.write_text(
                'version = "0.1"\n'
                'default_command = "codex"\n'
                'capture_transcript = true\n',
                encoding="utf-8",
            )

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def read_json(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def discover(cls, start: Path | None = None) -> "TrailWorkspace":
        base = Path.cwd() if start is None else start
        return cls(root=_find_project_root(base))
