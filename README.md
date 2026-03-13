# Trail

Persistent work context for Codex.

Trail is a Codex-first wrapper that watches work, records structured events, rebuilds project state, and prepares clean handoffs after compaction or session changes.

## Current MVP

- `trail init` creates `.trail/`
- `~/.trail/` stores the global Trail library for skills, projects, and conversations
- `trail attach <skill>` bootstraps the current project with a linked skill and default specialist agent
- `trail work <skill> "task"` opens Codex with Trail already attached and contextualized
- `trail` with no arguments launches `codex`
- `trail run` wraps an interactive command, defaulting to `codex`
- `trail mcp` exposes Trail as a local MCP server
- `.trail/events.jsonl` is the source of truth
- `.trail/state/*.json` stores materialized state
- `trail status` shows current state
- `trail checkpoint` and `trail handoff` create durable snapshots
- `trail note ...` records goals, decisions, blockers, docs, and specs
- `trail skill run <skill>` launches `codex` with a skill briefing built from Trail state
- `trail skill add/list/show/link` manages the global skill library
- `trail project init/list/show/link-skill` manages global project records
- `trail convo save/list/show/fetch` manages global conversation records
- `trail agent add/list/show/link/run` manages specialized project agents

## Usage

```bash
trail init
trail attach rag-docs-api --goal "Ship Trail MVP" --next-step "Create the first two real project conversations"
trail work rag-docs-api "Check the RAG API readiness flow"
trail work rag-docs-api --use-agent "Prepare a manager-ready status update"
```

## Next

- stronger session parsing
- richer project- and skill-aware context packs
- doc/spec ingestion beyond manual notes
- specialized project agents on top of linked skills and conversations
- multi-agent orchestration over shared Trail context

## Specs

- [TRAIL_V0.2.md](./TRAIL_V0.2.md): Trail as the reference layer for skills, conversations, context, and sync
- [TRAIL_MCP_V0.1.md](./TRAIL_MCP_V0.1.md): How Codex should call Trail during a live session through MCP
- [TRAIL_SKILL_USAGE_V0.1.md](./TRAIL_SKILL_USAGE_V0.1.md): Standard Trail orchestration rules for runtime bootstrap and skill briefings
- [WINDOWS_LOCAL_TEST.md](./WINDOWS_LOCAL_TEST.md): Native Windows install and first real local project test
