# Trail v0.2

Trail is the reference layer for skill tracking, conversation memory, and working context around Codex.

This version reframes Trail from "wrapper around Codex" to "source of truth for skills, conversations, context, and sync".

## Core Positioning

Trail is not only a local CLI.

Trail is:

- a skill library
- a conversation store
- a context engine
- a project linker
- a sync layer

Codex remains the execution engine.
Trail becomes the persistent memory and organizational layer around it.

## Product Statement

Trail should answer these questions at any time:

- Which skills do I have?
- Which projects are linked to each skill?
- Which conversations matter for this skill or project?
- What was already done, what is in progress, and what is next?
- Which docs and specs are relevant here?
- What should the next Codex instance know immediately?

## Core Entities

Trail v0.2 is built around six primary entities:

- `Skill`
- `Project`
- `Conversation`
- `ContextPack`
- `Knowledge`
- `SyncRecord`

The product should treat these as first-class objects, not as incidental files.

## 1. Skill

A skill is no longer just a `SKILL.md`.

A Trail skill is a durable object with metadata, links, memory, and usage history.

### Skill fields

```json
{
  "id": "skill_rag_docs_api",
  "slug": "rag-docs-api",
  "title": "RAG Docs API",
  "source": {
    "kind": "local_codex_skill",
    "path": "/home/ubuntu/.codex/skills/rag-docs-api/SKILL.md"
  },
  "description": "Query or ingest docs for a RunMesh RAG HTTP API.",
  "tags": ["docs", "rag", "api"],
  "version": "local",
  "linked_projects": ["proj_trail"],
  "linked_conversations": ["conv_20260313_001"],
  "linked_knowledge": ["know_runmesh_api"],
  "status": "active"
}
```

### Skill responsibilities

- describe how to work
- know which projects it belongs to
- know which docs/specs matter
- remember prior attempts and decisions
- produce a skill-specific context briefing

## 2. Project

A project is the durable container for goals, repos, tasks, risks, and linked skills.

### Project fields

```json
{
  "id": "proj_trail",
  "slug": "trail",
  "title": "Trail",
  "root": "/home/ubuntu/trail",
  "repo": {
    "git": true,
    "remote": null,
    "default_branch": "main"
  },
  "status": "active",
  "goals": [
    "Make Trail the reference for skill tracking and context"
  ],
  "linked_skills": ["skill_rag_docs_api"],
  "linked_conversations": ["conv_20260313_001"],
  "owners": ["ubuntu"],
  "tags": ["codex", "memory", "cli"]
}
```

### Project responsibilities

- track current goals
- track repo-specific context
- group conversations and skills
- support manager-ready status

## 3. Conversation

A conversation is the durable record of a Codex work session or thread.

Conversations must be fetchable later by:

- skill
- project
- repo
- topic
- date

### Conversation fields

```json
{
  "id": "conv_20260313_001",
  "session_id": "sess_fa646a8206",
  "project_id": "proj_trail",
  "skill_ids": ["skill_rag_docs_api"],
  "title": "Design Trail as skill and conversation registry",
  "status": "open",
  "started_at": "2026-03-13T20:00:00Z",
  "updated_at": "2026-03-13T20:15:00Z",
  "current_goal": "Define Trail v0.2 data model",
  "summary": "Reframed Trail from wrapper to memory and sync layer.",
  "next_step": "Implement local registries for skills and projects.",
  "blockers": [],
  "transcript_ref": ".trail/transcripts/sess_fa646a8206.log",
  "handoff_refs": [
    ".trail/handoffs/2026-03-13T20-06-10Z_initial-handoff.md"
  ],
  "tags": ["architecture", "trail", "skills"]
}
```

### Conversation responsibilities

- preserve the work thread
- preserve checkpoints and handoffs
- preserve state transitions
- support refetch and resume

## 4. ContextPack

A `ContextPack` is the exact package injected into Codex or a skill at execution time.

This should be generated, versioned, and explainable.

### ContextPack fields

```json
{
  "id": "ctx_20260313_001",
  "project_id": "proj_trail",
  "conversation_id": "conv_20260313_001",
  "skill_id": "skill_rag_docs_api",
  "generated_at": "2026-03-13T20:20:00Z",
  "goal": "Define Trail v0.2 data model",
  "current_state": "Spec drafting in progress",
  "important_decisions": [
    "Trail is the source of truth for skills, conversations, and context"
  ],
  "open_blockers": [],
  "failed_attempts": [],
  "relevant_files": [
    "/home/ubuntu/trail/README.md",
    "/home/ubuntu/trail/TRAIL_V0.2.md"
  ],
  "relevant_knowledge_ids": ["know_runmesh_api"]
}
```

### ContextPack responsibilities

- carry only the relevant context
- be cheap to regenerate
- be explainable to the user
- be stable across compaction and restart

## 5. Knowledge

Knowledge represents retained facts from docs, specs, tickets, and prior work.

Knowledge should not be a loose vector blob by default.
It should be structured and linkable.

### Knowledge fields

```json
{
  "id": "know_runmesh_api",
  "kind": "external_doc",
  "source": {
    "label": "RunMesh API reference",
    "path": "/home/ubuntu/.codex/skills/rag-docs-api/references/runmesh-api.md"
  },
  "topic": "RunMesh RAG API",
  "facts": [
    "GET /api/status returns readiness metadata",
    "POST /api/ask requires prompt, limit, and sessionId",
    "project, messages, and images are optional"
  ],
  "linked_skills": ["skill_rag_docs_api"],
  "linked_projects": ["proj_trail"],
  "confidence": "fact",
  "updated_at": "2026-03-13T20:20:00Z"
}
```

### Knowledge responsibilities

- retain important facts
- link facts to the right skills and projects
- support recall without replaying the whole transcript
- support confidence labeling

## 6. SyncRecord

Trail should support cloud persistence, but cloud is not the source of truth for v0.2.

Cloud is a synchronization and retrieval layer.

### SyncRecord fields

```json
{
  "id": "sync_20260313_001",
  "entity_kind": "conversation",
  "entity_id": "conv_20260313_001",
  "backend": "trail_cloud",
  "status": "synced",
  "last_pushed_at": "2026-03-13T20:30:00Z",
  "last_pulled_at": null,
  "etag": "sha256:abc123",
  "version": 3
}
```

### Sync responsibilities

- push local objects to cloud
- fetch them later on another machine
- preserve references and versions
- support conflict detection

## Relationship Model

The important thing is not only storing entities, but linking them.

### Required links

- `Skill -> Project`
- `Skill -> Conversation`
- `Skill -> Knowledge`
- `Project -> Conversation`
- `Project -> Knowledge`
- `Conversation -> ContextPack`
- `Conversation -> Handoff`

### Link examples

```json
{
  "id": "link_001",
  "from_kind": "skill",
  "from_id": "skill_rag_docs_api",
  "to_kind": "project",
  "to_id": "proj_trail",
  "relation": "used_in",
  "created_at": "2026-03-13T20:30:00Z"
}
```

Trail should treat links as explicit data, not inferred only at runtime.

## Storage Topology

Trail needs three layers of storage.

## A. Repo-local state

Lives in `.trail/` inside a project repo.

Purpose:

- current work state
- repo-scoped events
- transcripts
- checkpoints
- handoffs

### Repo-local layout

```text
.trail/
  events.jsonl
  state/
    current.json
  conversations/
    current.json
    conv_*.json
  context/
    current.json
  knowledge/
    *.json
  handoffs/
    *.json
    *.md
  transcripts/
    *.log
```

## B. User-global library

Lives outside any repo, for example in `~/.trail/`.

Purpose:

- global skill registry
- global conversation index
- project registry
- sync metadata

### User-global layout

```text
~/.trail/
  skills/
    registry.json
    objects/
      skill_*.json
  projects/
    registry.json
    objects/
      proj_*.json
  conversations/
    index.json
    objects/
      conv_*.json
  knowledge/
    objects/
      know_*.json
  sync/
    records.json
  config.toml
```

## C. Cloud store

Purpose:

- backup
- cross-device continuity
- team sharing later
- refetch old conversations and skill state

v0.2 does not need a full backend spec yet, but all objects should already be shaped for future upload.

## Data Ownership Rules

To avoid confusion later, ownership rules should be explicit.

- repo-local state owns the raw execution trail for that repo
- global library owns reusable skill, project, and conversation indexes
- cloud owns replicated copies, not the initial truth

## Conversation Model

Conversations are central.

Trail should support both:

- local transcript capture
- logical conversation objects

These are not the same thing.

The transcript is the raw stream.
The conversation object is the structured handle for retrieval, state, and linking.

### Conversation lifecycle

1. conversation starts
2. transcript/log stream begins
3. events accumulate
4. state evolves
5. checkpoints or handoffs are created
6. conversation is closed or parked
7. conversation can be refetched later

## Skill Library Model

Trail should support a proper skill library.

### A skill can come from

- a local Codex skill directory
- a repo file
- a cloud-synced Trail skill
- a generated skill pack in the future

### A skill library entry should include

- metadata
- source path or remote URI
- support files
- linked conversations
- linked projects
- local notes or overrides

## Cloud Sync Model

Cloud sync should be selective and object-based.

### Minimum syncable objects

- skills
- projects
- conversations
- handoffs
- context packs
- knowledge entries

### Not required at first

- raw shell logs by default
- every event line by default

Raw logs are often too noisy or too sensitive.
Trail should sync structured objects first, with optional transcript upload later.

## Privacy and Secrets

Cloud sync introduces real risk.

Trail should default to:

- local-only unless sync is configured
- no secrets in structured summaries
- transcript sync opt-in
- explicit redaction hooks later

## CLI Surface for v0.2

The CLI should reflect the new model.

### Skill commands

- `trail skill list`
- `trail skill show <skill>`
- `trail skill add <path-or-name>`
- `trail skill link <skill> <project>`
- `trail skill context <skill>`

### Project commands

- `trail project list`
- `trail project init`
- `trail project show <project>`
- `trail project link-skill <project> <skill>`

### Conversation commands

- `trail convo current`
- `trail convo list`
- `trail convo show <conversation>`
- `trail convo save`
- `trail convo fetch <conversation>`
- `trail convo link-skill <conversation> <skill>`

### Context commands

- `trail context build`
- `trail context show`
- `trail context export`

### Knowledge commands

- `trail know add-doc`
- `trail know add-spec`
- `trail know list`
- `trail know recall <topic>`

### Sync commands

- `trail sync status`
- `trail sync push`
- `trail sync pull`

## Execution Model

Codex execution now becomes one use of Trail, not the whole definition of Trail.

### Execution path

1. Trail resolves skill + project + conversation
2. Trail builds a ContextPack
3. Codex receives the ContextPack plus the skill instructions
4. Trail stores the resulting conversation and updated links

This means `trail` can still launch `codex`, but `trail` is no longer defined by that wrapper alone.

## Success Criteria

Trail is working when:

- a skill can be reopened with full context
- an old conversation can be refetched later
- the user can ask "what happened on this project?" and get a reliable answer
- the user can ask "which conversations matter for this skill?" and get a precise answer
- the user can switch machines and continue work

## MVP Boundary for v0.2

Trail v0.2 should include:

- explicit skill objects
- explicit project objects
- explicit conversation objects
- explicit links
- local global registry under `~/.trail/`
- repo-local state under `.trail/`
- object-shaped sync metadata

Trail v0.2 should not yet require:

- a full hosted backend
- team collaboration
- vector search as the primary retrieval mode
- automatic transcript understanding of everything

## Immediate Implementation Direction

The next code changes should target these steps:

1. Add a user-global `~/.trail/` registry layer.
2. Add `skill`, `project`, and `convo` objects as JSON documents.
3. Make `trail skill add/show/link` update these registries.
4. Make `trail convo save` produce a durable conversation object from current repo state.
5. Add `context/current.json` generation from linked objects.
6. Add stub `sync` records and commands.

## Summary

Trail v0.2 defines Trail as the reference system for:

- skill library
- conversation tracking
- project context
- knowledge retention
- cross-session continuity
- future cloud sync

Codex stays the worker.
Trail becomes the memory and the map.
