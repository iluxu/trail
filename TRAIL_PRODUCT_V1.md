# Trail Product V1

## Positioning

Trail is the persistent memory and orchestration layer for Codex.

Codex executes.
Skills provide method.
Trail provides continuity, project memory, specialist context, audit knowledge, and reporting.

The product promise is simple:

- launch `trail`
- Codex knows where the project stands
- Codex knows what was done, what remains, and what is risky
- Codex can recover after compaction or a new session
- Codex can act like a specialist instead of a stateless chat

## Product Thesis

Skills are not enough on their own.

A skill can describe how to work, but not:

- what happened yesterday
- which decisions were already made
- which blockers are still open
- which migration gaps are already known
- which conventions are specific to this project
- what to tell a manager right now

Trail turns a static skill into cumulative project expertise.

## Core Objects

Trail revolves around six persistent objects:

- `Skill`
  The reusable method layer.
- `Project`
  The working unit with status, goals, and linked context.
- `Conversation`
  A recoverable work thread across Codex sessions.
- `Context Pack`
  The minimal truth Codex should load at startup.
- `Knowledge Pack`
  Structured project or domain knowledge, docs, specs, rules, gaps, and reference patterns.
- `Agent`
  A specialist view over the same shared Trail truth.

## Product Modes

Trail should feel like one product with three dominant modes.

### 1. Build

Use when coding, debugging, or shipping.

Main value:

- resume work instantly
- remember decisions and blockers
- keep project-specific conventions attached to the skill
- avoid repeating failed attempts

Typical asks:

- continue the last task
- explain current project state
- fix this screen without breaking known patterns
- prepare the next safe change

### 2. Audit

Use when checking parity, correctness, migration quality, design-system compliance, or runtime risk.

Main value:

- compare expected behavior versus actual implementation
- separate visible migration polish from real business correctness
- keep a durable audit trail over multiple sessions
- produce checklist-based findings

Typical asks:

- audit this migrated screen against business rules
- check this diff against EUI21 conventions
- list migration gaps that still need runtime verification
- verify old project behavior was preserved

### 3. Report

Use when preparing updates, handoffs, or management-facing summaries.

Main value:

- produce a clean status without reloading context manually
- summarize done, doing, risks, and next steps
- generate handoffs for the next Codex instance or teammate

Typical asks:

- what do I tell my manager
- what changed since the last session
- what is blocking delivery
- what should happen next

## Killer Features

These are the features that make Trail feel like a real product instead of a wrapper.

### Startup Brief

When launched through `trail`, Codex should always know:

- active project
- active skill
- active agent
- active audit or knowledge packs
- recent conversations
- current goal
- next step
- open blockers

### Living Skill Overlay

Every global skill should gain a local overlay from Trail:

- project-specific conventions
- local docs and rules
- known good patterns
- known bad patterns
- current objectives
- linked conversations

The overlay is the real "skill-local super personalized" layer.

### Recoverable Conversations

Conversations should not die with a session.

Trail should let Codex:

- refetch a prior conversation
- see the important decisions and outcomes
- continue from the last meaningful state
- fork a new thread from previous work

### Knowledge Packs

Knowledge should be structured and reusable.

Examples:

- migration audit packs
- backend architecture packs
- API contract packs
- incident runbooks
- repo-proven pattern packs

### Specialist Agents

Agents are not separate memories.
They are specialist views over the same Trail truth.

Examples:

- `migration-auditor`
- `manager-reporter`
- `runtime-debugger`
- `ui-conventions-checker`
- `business-rules-checker`
- `delivery-lead`

### Automatic Recording

Trail should capture important events with minimal user effort:

- decisions
- blockers
- next steps
- findings
- handoffs
- major failures

The user should not have to narrate everything manually.

## The Dream UX

The ideal experience is:

```text
trail
```

Then the user can say:

- audit this migration
- continue the last task
- summarize project status
- check this diff against conventions
- tell me what remains risky
- prepare an update for my manager

And Codex should already know enough to start correctly.

## Product Principles

### Truth over vibes

Trail must be a source of truth, not a vague memory aid.

### Local first

The repo and user machine remain the center of gravity.

### Structured over raw transcript

Event logs, checklists, findings, and knowledge packs matter more than giant freeform summaries.

### Codex-first

Trail exists to make Codex stronger, not to compete with it.

### Minimal user ceremony

The user should not need ten commands per session.

## V1 Feature Set

The V1 product should ship with the following capabilities.

### Runtime

- `trail` launches Codex with Trail MCP attached
- startup brief available immediately
- active project and skill inferred from local state

### Memory

- local `.trail/` state
- global `~/.trail/` registry
- conversations linked to projects and skills
- durable handoffs and checkpoints

### Audit

- migration pack setup
- knowledge search over imported rules, gaps, and flows
- audit prompt generation
- checklist and report template generation

### Agents

- per-project specialist agents
- linked to shared project context
- launchable from Trail

### Reporting

- manager-ready status
- reusable handoff generation

## Roadmap

### Phase 1: Make the current flow invisible

- remove visible bootstrap clutter
- make Codex call Trail naturally at startup
- improve Windows reliability
- improve transcript and event capture

### Phase 2: Auto-write

- record decisions automatically when Codex states a clear conclusion
- record blockers automatically from failed actions
- record next steps automatically when a plan stabilizes
- save handoff automatically when a session closes

### Phase 3: Audit engine

- `trail audit migration`
- `trail audit diff`
- `trail audit screen`
- `trail audit report`

### Phase 4: Reporting engine

- `trail report status`
- `trail report manager`
- `trail report risks`
- `trail report weekly`

### Phase 5: Knowledge ingestion machine

- ingest docs from URLs, markdown, repos, and tickets
- distill facts, constraints, gotchas, and recipes
- link them to skills, projects, and agents

### Phase 6: Real multi-agent collaboration

- coordinated specialist agents
- shared Trail truth
- explicit task decomposition
- consolidated findings

## Immediate Next Build Priorities

If the goal is to move fastest from "working demo" to "product people want", the next priorities should be:

1. Hide the MCP/bootstrap rough edges so `trail` feels native.
2. Make Trail auto-record decisions, blockers, and next steps.
3. Add a first-class `manager-reporter` agent and report commands.
4. Add first-class audit commands instead of prompt-only flows.
5. Add project-local overlay files in `.trail/overlays/`.

## Tagline Options

- Trail makes Codex cumulative.
- Trail gives Codex project memory.
- Trail turns skills into persistent expertise.
- Trail is the memory layer for Codex.
