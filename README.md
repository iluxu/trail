# Trail

Persistent work context for Codex.

Trail gives Codex durable project memory.
It tracks sessions, records structured events, rebuilds project state, and generates clean handoffs so context survives compaction, restarts, and long-running work.

## Current MVP

- `trail init` creates `.trail/`
- `~/.trail/` stores the global Trail library for skills, projects, and conversations
- `trail attach <skill>` bootstraps the current project with a linked skill and default specialist agent
- `trail work <skill> "task"` opens Codex with Trail already attached and contextualized
- `trail migration setup [skill]` turns 4 markdown sources into a reusable local audit pack
- `trail migration run "task"` opens Codex as a migration auditor with Trail MCP attached
- `trail` with no arguments launches `codex`, attaches Trail MCP, and tells Codex to start by calling `trail_get_startup_brief`
- `trail overlay ...` manages the local dynamic skill overlay in `.trail/skills/overlays/`
- `trail pack ...` manages local project packs in `.trail/packs/`
- `trail report manager` generates a manager-ready project report
- `trail report audit` generates the current audit posture from Trail findings and packs
- `trail report risks` generates the current Trail risk register
- `trail resume` generates the concise restart brief for the next Codex instance
- `trail finding ...` records and lists structured audit findings
- `trail audit screen ...` and `trail audit diff ...` run first-class audits with Trail context
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
trail migration setup frontend-audit --goal "Audit migrated project parity" --next-step "Validate the checkout and reporting flows"
trail migration run "Check whether the migrated project preserves the old business rules"
trail overlay update frontend-audit --project-summary "Migration project" --directive "Use repo-proven UI and workflow patterns"
trail pack import delivery-rules --file references/delivery.md --activate
trail report manager
trail report audit
trail report risks
trail resume
trail finding add "Checkout totals still drift after refresh" --severity high --status open --category migration
trail audit screen "Checkout > Review > Payment" --dry-run
trail audit diff --base HEAD~1 --dry-run
trail
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
- [TRAIL_PRODUCT_V1.md](./TRAIL_PRODUCT_V1.md): Product vision, modes, killer features, and build order
- [WINDOWS_LOCAL_TEST.md](./WINDOWS_LOCAL_TEST.md): Native Windows install and first real local project test
