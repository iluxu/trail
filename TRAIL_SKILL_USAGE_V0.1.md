# Trail Skill Usage v0.1

This document defines how Codex should be prompted to use Trail well.

The rule is simple:

- runtime orchestration tells Codex when to use Trail in general
- skill usage tells Codex how to use Trail for a specific skill
- MCP tool descriptions reinforce the decision at tool-selection time

Trail should not rely on only one of these layers.

## Orchestration Layers

### 1. Runtime bootstrap

Injected by `trail run`.

Purpose:

- establish that Trail is attached
- tell Codex to fetch context and write back important facts
- keep the instruction short and policy-like

### 2. Skill-level Trail Usage

Injected into a skill briefing.

Purpose:

- make Trail part of the skill workflow
- teach Codex how to use Trail during specialist work

### 3. MCP tool descriptions

Provided by the Trail MCP server.

Purpose:

- remind Codex when each tool should be used
- reduce dependence on prompt wording alone

## Standard Trail Usage Section

This section should be injected into skill briefings and reused as a convention.

```text
Trail Usage:
- At the start, call Trail to fetch current context before making project-state assumptions.
- Before deep skill work, call Trail to fetch skill context if it is available.
- Before answering from memory about docs or specs, call Trail to search retained knowledge.
- After an important decision, record it in Trail.
- When you discover a blocker, record it in Trail.
- Before ending or parking the task, save a Trail handoff.
```

## Runtime Bootstrap Prompt

The runtime bootstrap should stay short.

Reference version:

```text
Trail is attached as your project memory layer.
Use it instead of relying on memory alone.
- At the start, call Trail to fetch current context before making project-state assumptions.
- Before deep skill work, call Trail to fetch skill context if it is available.
- Before answering from memory about docs or specs, call Trail to search retained knowledge.
- After an important decision, record it in Trail.
- When you discover a blocker, record it in Trail.
- Before ending or parking the task, save a Trail handoff.
```

## Why this matters

Without this structure:

- Codex may ignore Trail
- Codex may rely on memory alone
- skills become inconsistent in how they use Trail

With this structure:

- Trail becomes part of the execution loop
- skill usage becomes more consistent
- project memory gets better over time

## Future extension

Later, Trail can add automatic reminders or guards if:

- Codex is ending a task without a handoff
- Codex made several decisions without recording them
- Codex is answering a doc/spec question without checking Trail knowledge first
