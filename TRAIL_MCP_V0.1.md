# Trail MCP v0.1

Trail and Codex should work in a closed loop.

If `trail` launches `codex`, then Codex should be able to call Trail directly during the session.

This document defines the first MCP contract for Trail.

## Goal

When a Trail-managed Codex session starts:

1. Trail prepares local and global context.
2. Trail exposes an MCP server for this session.
3. Codex sees Trail as a tool provider.
4. Codex can read and write project memory through Trail.
5. Trail remains the source of truth for skill, conversation, and context state.

## Product Rule

Codex should not invent project memory when Trail is available.

Codex should call Trail to:

- fetch context
- fetch prior conversations
- fetch linked knowledge
- record decisions
- record blockers
- record next steps
- save handoffs

## Runtime Model

`trail run` should do the following:

1. resolve current project and active skill, if any
2. build a fresh `ContextPack`
3. start a local Trail MCP server
4. launch Codex with that MCP server attached
5. inject a short initial instruction telling Codex when to use Trail
6. keep updating Trail state while the session runs

## High-Level Architecture

### Components

- `trail run`
  Starts the session and launches Codex
- `trail mcp`
  Local MCP server exposing Trail tools
- `trail store`
  Reads and writes `.trail/` and `~/.trail/`
- `trail reducer`
  Rebuilds current state from events and linked objects

## MCP Tool Design Principles

- tools should map to real Trail objects
- tools should stay small and explicit
- read tools and write tools should be separate
- tools should return structured JSON
- write tools should create events as well as update materialized state

## Tool Names

Use a stable `trail_*` naming convention so Codex can reason about them clearly.

## Initial Read Tools

### `trail_get_current_context`

Returns the current context pack for the active project/session.

#### Input

```json
{}
```

#### Output

```json
{
  "project_id": "proj_trail",
  "conversation_id": "conv_20260313_001",
  "skill_id": "skill_rag_docs_api",
  "goal": "Define Trail MCP integration",
  "current_state": "Spec drafting in progress",
  "next_step": "Implement local MCP server",
  "open_blockers": [],
  "recent_decisions": [],
  "recent_failures": []
}
```

### `trail_get_skill_context`

Returns the enriched context for a specific skill.

#### Input

```json
{
  "skill": "rag-docs-api"
}
```

#### Output

```json
{
  "skill": {
    "id": "skill_rag_docs_api",
    "slug": "rag-docs-api",
    "description": "Query or ingest docs for a RunMesh RAG HTTP API."
  },
  "linked_projects": ["proj_trail"],
  "linked_conversations": ["conv_20260313_001"],
  "linked_knowledge": ["know_runmesh_api"],
  "briefing": "..."
}
```

### `trail_list_project_conversations`

Returns recent or linked conversations for a project.

#### Input

```json
{
  "project": "trail",
  "limit": 10
}
```

#### Output

```json
{
  "items": [
    {
      "id": "conv_20260313_001",
      "title": "Design Trail as skill and conversation registry",
      "status": "open",
      "updated_at": "2026-03-13T20:15:00Z",
      "next_step": "Implement local registries for skills and projects."
    }
  ]
}
```

### `trail_fetch_conversation`

Fetches one conversation object and its key state.

#### Input

```json
{
  "conversation_id": "conv_20260313_001"
}
```

#### Output

```json
{
  "conversation": {
    "id": "conv_20260313_001",
    "title": "Design Trail as skill and conversation registry",
    "summary": "Reframed Trail as skill, conversation, and context reference layer.",
    "next_step": "Implement local registries.",
    "blockers": []
  }
}
```

### `trail_search_knowledge`

Searches retained knowledge entries by topic, skill, or project.

#### Input

```json
{
  "query": "RAG API required fields",
  "skill": "rag-docs-api",
  "limit": 5
}
```

#### Output

```json
{
  "items": [
    {
      "id": "know_runmesh_api",
      "topic": "RunMesh RAG API",
      "facts": [
        "POST /api/ask requires prompt, limit, and sessionId",
        "project, messages, and images are optional"
      ],
      "source": {
        "path": "/home/ubuntu/.codex/skills/rag-docs-api/references/runmesh-api.md"
      }
    }
  ]
}
```

## Initial Write Tools

### `trail_record_decision`

Records a project or skill decision.

#### Input

```json
{
  "summary": "Use MCP between Trail and Codex",
  "reason": "Codex must fetch and persist context directly",
  "impact": "Trail becomes part of the execution loop",
  "skill": "rag-docs-api"
}
```

#### Output

```json
{
  "ok": true,
  "event_id": "evt_123"
}
```

### `trail_record_blocker`

Records an open blocker.

#### Input

```json
{
  "summary": "Need a local MCP server implementation",
  "severity": "medium",
  "owner": "trail"
}
```

#### Output

```json
{
  "ok": true,
  "blocker_id": "blocker_001",
  "event_id": "evt_124"
}
```

### `trail_record_next_step`

Stores the next best action.

#### Input

```json
{
  "summary": "Implement trail_get_current_context MCP tool"
}
```

#### Output

```json
{
  "ok": true,
  "event_id": "evt_125"
}
```

### `trail_save_handoff`

Creates a handoff object and returns its refs.

#### Input

```json
{
  "label": "end-of-session"
}
```

#### Output

```json
{
  "ok": true,
  "handoff": {
    "json_path": "/home/ubuntu/trail/.trail/handoffs/2026-03-13T20-30-00Z_end-of-session.json",
    "md_path": "/home/ubuntu/trail/.trail/handoffs/2026-03-13T20-30-00Z_end-of-session.md"
  }
}
```

## Optional Early Tools

These are useful soon, but not required for the first loop.

- `trail_link_skill_project`
- `trail_convo_save`
- `trail_convo_fetch_latest`
- `trail_get_manager_status`

## When Codex Should Call Trail

Codex should be instructed to use Trail:

- at the start of a session to fetch current context
- before using a skill to fetch skill context
- after making an important decision
- when discovering a blocker
- before ending a session to save handoff
- when it needs prior knowledge instead of guessing

## Initial Codex Instruction

Trail should inject a short instruction like:

> Trail is available as your project memory layer. Use it to fetch current context, fetch skill context, retrieve linked conversations and knowledge, and record important decisions, blockers, and next steps instead of relying on memory alone.

This should stay short.
The rest belongs in tools and context packs, not in the bootstrap prompt.

## MCP Server Shape

For v0.1, `trail mcp` can be a local stdio server.

That keeps things simple and matches how Codex already connects to external MCP servers.

## Local Session Scope

The MCP server should know:

- current repo root
- current project id
- current conversation id
- active skill id if any

These values can be passed by environment variables or CLI flags from `trail run` to `trail mcp`.

## Suggested Session Environment

```text
TRAIL_PROJECT_ROOT=/home/ubuntu/trail
TRAIL_PROJECT_ID=proj_trail
TRAIL_CONVERSATION_ID=conv_20260313_001
TRAIL_SKILL_ID=skill_rag_docs_api
```

## State Consistency Rules

When Codex calls a write tool:

1. Trail writes a new event
2. Trail updates relevant object files
3. Trail rebuilds materialized state if needed
4. Trail returns the updated object or event reference

Write tools should never update only the snapshot and skip the event log.

## Failure Rules

If Trail does not know the answer:

- it should say so explicitly
- it should return an empty result or structured error
- Codex may continue, but should know this is a missing Trail fact

Trail should not fabricate missing conversations, knowledge, or links.

## First Implementation Boundary

The first code implementation should support:

- `trail_get_current_context`
- `trail_get_skill_context`
- `trail_search_knowledge`
- `trail_record_decision`
- `trail_record_blocker`
- `trail_record_next_step`
- `trail_save_handoff`

This is enough for a meaningful Codex ↔ Trail feedback loop.

## Next Implementation Steps

1. Build a local stdio MCP server for Trail.
2. Map the first read/write tools to current store functions.
3. Make `trail run` launch Codex with Trail MCP attached.
4. Add the short Codex bootstrap instruction.
5. Validate that Codex can fetch context and write back decisions during a live session.

## Summary

Trail should not only launch Codex.

Trail should be callable by Codex at runtime.

MCP is the clean contract that makes that possible.
