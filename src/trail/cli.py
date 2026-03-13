from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import uuid
from pathlib import Path

try:
    import pty
except ImportError:  # Windows
    pty = None

from .events import emit_event, utc_now
from .migration import (
    build_migration_prompt,
    load_migration_pack,
    setup_migration_pack,
)
from .mcp_server import run_stdio_server
from .operations import (
    build_context_pack,
    create_handoff,
    create_or_update_conversation,
    current_session_id,
    fetch_conversation_to_workspace,
    init_workspace,
    load_state,
    record_blocker,
    record_decision,
    record_next_step,
    sync_conversation_to_registry,
)
from .registry import global_registry
from .reducer import reduce_state
from .skills import build_skill_briefing, resolve_skill, trail_usage_guidance
from .workspace import TrailWorkspace


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _session_payload(
    session_id: str,
    root: Path,
    command: list[str],
    *,
    conversation_id: str | None = None,
    skill_name: str | None = None,
) -> dict:
    return {
        "session_id": session_id,
        "project_root": str(root),
        "started_at": utc_now(),
        "command": command,
        "conversation_id": conversation_id,
        "skill_name": skill_name,
    }


def cmd_init(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover(Path(args.path).resolve() if args.path else None)
    init_workspace(workspace)
    print(f"Initialized Trail workspace in {workspace.trail_dir}")
    return 0


def _build_run_command(args: argparse.Namespace) -> list[str]:
    if args.command:
        command = list(args.command)
        if command and command[0] == "--":
            command = command[1:]
        if command:
            return command
    return ["codex"]


def _trail_python() -> str:
    return sys.executable


def _trail_module_args() -> list[str]:
    return ["-m", "trail.cli", "mcp"]


def _trail_mcp_env(workspace: TrailWorkspace, *, conversation_id: str, skill_name: str | None) -> dict[str, str]:
    env = {
        "TRAIL_PROJECT_ROOT": str(workspace.root),
        "TRAIL_PROJECT_ID": f"proj_{workspace.root.name}",
        "TRAIL_CONVERSATION_ID": conversation_id,
    }
    if skill_name:
        env["TRAIL_SKILL_SLUG"] = skill_name
    return env


def _codex_bootstrap_prompt() -> str:
    lines = [
        "Trail is attached as your project memory layer.",
        "Use it instead of relying on memory alone.",
        *trail_usage_guidance()[1:],
    ]
    return "\n".join(lines)


def _is_codex_command(command: list[str]) -> bool:
    return bool(command) and Path(command[0]).name == "codex"


def _attach_trail_mcp(
    command: list[str],
    workspace: TrailWorkspace,
    *,
    conversation_id: str,
    skill_name: str | None,
    include_bootstrap_prompt: bool,
) -> list[str]:
    if not _is_codex_command(command):
        return command

    env = _trail_mcp_env(workspace, conversation_id=conversation_id, skill_name=skill_name)
    attached = [command[0]]
    attached.extend(
        [
            "-c",
            f"mcp_servers.trail.command={json.dumps(_trail_python())}",
            "-c",
            f"mcp_servers.trail.args={json.dumps(_trail_module_args())}",
            "-c",
            f"mcp_servers.trail.cwd={json.dumps(str(workspace.root))}",
        ]
    )
    for key, value in env.items():
        attached.extend(["-c", f"mcp_servers.trail.env.{key}={json.dumps(value)}"])

    attached.extend(command[1:])
    if include_bootstrap_prompt and len(command) == 1:
        attached.append(_codex_bootstrap_prompt())
    return attached


def _spawn_with_transcript(command: list[str], transcript_path: Path) -> int:
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt" or pty is None:
        return _spawn_windows(command, transcript_path)

    transcript = transcript_path.open("ab")

    def read_from_master(fd: int) -> bytes:
        data = os.read(fd, 1024)
        if data:
            transcript.write(data)
            transcript.flush()
        return data

    try:
        try:
            status = pty.spawn(command, master_read=read_from_master)
        except FileNotFoundError:
            transcript.write(f"Command not found: {command[0]}\n".encode("utf-8"))
            transcript.flush()
            return 127
    finally:
        transcript.close()
    return os.waitstatus_to_exitcode(status) if os.WIFEXITED(status) else 1


def _spawn_windows(command: list[str], transcript_path: Path) -> int:
    with transcript_path.open("ab") as transcript:
        transcript.write(
            (
                "Windows native run\n"
                f"Command: {shlex.join(command)}\n"
                "Transcript capture is currently metadata-only on Windows; interactive stdout/stderr is sent directly to the console.\n\n"
            ).encode("utf-8")
        )
        transcript.flush()
        try:
            completed = subprocess.run(command, check=False)
        except FileNotFoundError:
            transcript.write(f"Command not found: {command[0]}\n".encode("utf-8"))
            transcript.flush()
            return 127
        transcript.write(f"\nProcess exited with code {completed.returncode}\n".encode("utf-8"))
        transcript.flush()
        return int(completed.returncode)


def cmd_run(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    registry = global_registry()
    project_record = registry.upsert_project(workspace.root)

    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    conversation_id = f"conv_{uuid.uuid4().hex[:10]}"
    skill_name = getattr(args, "skill_name", None)
    skill_record = None
    if skill_name:
        skill_record = registry.upsert_skill(skill_name)
        skill_record, project_record = registry.link_skill_project(skill_name, project_record["slug"])
    command = _build_run_command(args)
    command = _attach_trail_mcp(
        command,
        workspace,
        conversation_id=conversation_id,
        skill_name=skill_name,
        include_bootstrap_prompt=getattr(args, "bootstrap", False),
    )

    session_payload = _session_payload(
        session_id,
        workspace.root,
        command,
        conversation_id=conversation_id,
        skill_name=skill_name,
    )
    workspace.write_json(workspace.current_session_path, session_payload)
    workspace.write_json(workspace.sessions_dir / f"{session_id}.json", session_payload)

    conversation = create_or_update_conversation(
        workspace,
        conversation_id=conversation_id,
        session_id=session_id,
        project_id=project_record["id"],
        skill_id=skill_record["id"] if skill_record else None,
        title=args.goal or f"Trail session {conversation_id}",
        current_goal=args.goal,
        next_step=(workspace.read_json(workspace.current_state_path) or {}).get("next_step"),
        status="open",
    )
    sync_conversation_to_registry(workspace, conversation)
    build_context_pack(workspace, skill_name=skill_name, user_task=args.goal)

    emit_event(
        workspace,
        session_id=session_id,
        kind="session_started",
        payload={"command": command, "conversation_id": conversation_id, "skill": skill_name},
    )
    if args.goal:
        emit_event(
            workspace,
            session_id=session_id,
            kind="goal_set",
            payload={"goal": args.goal},
        )
    emit_event(
        workspace,
        session_id=session_id,
        kind="command_run",
        payload={"command": shlex.join(command)},
    )

    transcript_path = workspace.transcripts_dir / f"{session_id}.log"
    exit_code = _spawn_with_transcript(command, transcript_path)

    emit_event(
        workspace,
        session_id=session_id,
        kind="session_finished",
        payload={
            "command": shlex.join(command),
            "exit_code": exit_code,
            "transcript": str(transcript_path),
            "conversation_id": conversation_id,
        },
    )

    ended_payload = {
        **session_payload,
        "ended_at": utc_now(),
        "exit_code": exit_code,
        "transcript": str(transcript_path),
    }
    workspace.write_json(workspace.sessions_dir / f"{session_id}.json", ended_payload)
    workspace.write_json(workspace.current_session_path, ended_payload)

    conversation = create_or_update_conversation(
        workspace,
        conversation_id=conversation_id,
        session_id=session_id,
        project_id=project_record["id"],
        skill_id=skill_record["id"] if skill_record else None,
        title=args.goal or f"Trail session {conversation_id}",
        current_goal=args.goal,
        next_step=(workspace.read_json(workspace.current_state_path) or {}).get("next_step"),
        status="closed" if exit_code == 0 else "paused",
        transcript_ref=str(transcript_path),
    )
    sync_conversation_to_registry(workspace, conversation)

    if exit_code != 0:
        emit_event(
            workspace,
            session_id=session_id,
            kind="command_failed",
            payload={
                "command": shlex.join(command),
                "exit_code": exit_code,
                "error_signature": f"process exited with code {exit_code}",
                "notes": "Inspect the transcript for details.",
                "transcript": str(transcript_path),
            },
        )

    reduce_state(workspace)
    build_context_pack(workspace, skill_name=skill_name, user_task=args.goal)
    return exit_code


def _print_status(state: dict, manager: bool = False, brief: bool = False) -> None:
    goal = state.get("current_goal") or "No active goal recorded."
    next_step = state.get("next_step") or "No next step recorded."
    blockers = state.get("open_blockers") or []
    failures = state.get("recent_failures") or []
    decisions = state.get("recent_decisions") or []

    if manager:
        print("Project status")
        print(f"- Goal: {goal}")
        print(f"- In progress: active session {state.get('active_session') or 'none'}")
        print(f"- Blockers: {len(blockers)} open")
        print(f"- Recent failures: {len(failures)}")
        print(f"- Next: {next_step}")
        return

    if brief:
        print(f"Goal: {goal}")
        print(f"Blockers: {len(blockers)}")
        print(f"Recent failures: {len(failures)}")
        print(f"Next: {next_step}")
        return

    print(f"Project root: {state.get('project_root')}")
    print(f"Active session: {state.get('active_session') or 'none'}")
    print(f"Sessions: {state.get('session_count', 0)}")
    print(f"Events: {state.get('event_count', 0)}")
    print(f"Goal: {goal}")
    print(f"Next step: {next_step}")

    last_command = state.get("last_command")
    if last_command and last_command.get("command"):
        print(f"Last command: {last_command['command']}")

    print(f"Open blockers: {len(blockers)}")
    for blocker in blockers[-5:]:
        print(f"  - {blocker.get('summary') or blocker.get('id')}")

    print(f"Recent failures: {len(failures)}")
    for failure in failures[-5:]:
        print(f"  - {failure.get('command')} :: {failure.get('error_signature')}")

    print(f"Recent decisions: {len(decisions)}")
    for decision in decisions[-5:]:
        print(f"  - {decision.get('summary')}")


def cmd_status(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    state = load_state(workspace)
    _print_status(state, manager=args.manager, brief=args.brief)
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    state = load_state(workspace)
    label = args.label or "checkpoint"
    slug = label.replace(" ", "-").lower()
    path = workspace.checkpoints_dir / f"{utc_now().replace(':', '-')}_{slug}.json"
    payload = {
        "label": label,
        "created_at": utc_now(),
        "state": state,
    }
    workspace.write_json(path, payload)
    emit_event(
        workspace,
        session_id=state.get("active_session") or "manual",
        kind="checkpoint_created",
        payload={"label": label, "path": str(path)},
    )
    reduce_state(workspace)
    print(path)
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    label = args.label or "handoff"
    paths = create_handoff(workspace, label=label)
    print(paths["md_path"])
    return 0


def _manual_session_id(workspace: TrailWorkspace) -> str:
    return current_session_id(workspace)


def cmd_note_goal(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    emit_event(
        workspace,
        session_id=_manual_session_id(workspace),
        kind="goal_set",
        payload={"goal": args.goal},
    )
    reduce_state(workspace)
    print("Recorded goal.")
    return 0


def cmd_note_next_step(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    record_next_step(workspace, summary=args.summary)
    print("Recorded next step.")
    return 0


def cmd_note_decision(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    record_decision(workspace, summary=args.summary, reason=args.reason, impact=args.impact)
    print("Recorded decision.")
    return 0


def cmd_note_blocker(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    record_blocker(
        workspace,
        summary=args.summary,
        blocker_id=args.id,
        severity=args.severity,
        owner=args.owner,
        workaround=args.workaround,
    )
    print("Recorded blocker.")
    return 0


def cmd_note_unblock(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    emit_event(
        workspace,
        session_id=_manual_session_id(workspace),
        kind="blocker_resolved",
        payload={"id": args.id},
    )
    reduce_state(workspace)
    print("Resolved blocker.")
    return 0


def _fact_payload(args: argparse.Namespace) -> dict:
    return {
        "source": args.source,
        "topic": args.topic,
        "facts": args.fact or [],
    }


def cmd_note_doc(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    emit_event(
        workspace,
        session_id=_manual_session_id(workspace),
        kind="doc_learned",
        payload=_fact_payload(args),
    )
    reduce_state(workspace)
    print("Recorded doc facts.")
    return 0


def cmd_note_spec(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    emit_event(
        workspace,
        session_id=_manual_session_id(workspace),
        kind="spec_learned",
        payload=_fact_payload(args),
    )
    reduce_state(workspace)
    print("Recorded spec facts.")
    return 0


def cmd_skill_show(args: argparse.Namespace) -> int:
    registry = global_registry()
    record = registry.get_skill(args.skill_name)
    if record:
        _print_json(record)
        return 0
    skill = resolve_skill(args.skill_name)
    print(skill.path)
    return 0


def cmd_skill_list(args: argparse.Namespace) -> int:
    registry = global_registry()
    _print_json({"items": registry.list_skills()})
    return 0


def cmd_skill_add(args: argparse.Namespace) -> int:
    registry = global_registry()
    record = registry.upsert_skill(args.skill_name)
    _print_json(record)
    return 0


def cmd_skill_link(args: argparse.Namespace) -> int:
    registry = global_registry()
    skill, project = registry.link_skill_project(args.skill_name, args.project)
    _print_json({"skill": skill, "project": project})
    return 0


def cmd_project_init(args: argparse.Namespace) -> int:
    registry = global_registry()
    root = Path(args.path).resolve() if args.path else TrailWorkspace.discover().root
    record = registry.upsert_project(root, title=args.title, slug=args.slug)
    _print_json(record)
    return 0


def cmd_project_list(args: argparse.Namespace) -> int:
    registry = global_registry()
    _print_json({"items": registry.list_projects()})
    return 0


def cmd_project_show(args: argparse.Namespace) -> int:
    registry = global_registry()
    identifier = args.project or str(TrailWorkspace.discover().root)
    record = registry.get_project(identifier)
    if not record:
        raise SystemExit(f"Project not found: {identifier}")
    _print_json(record)
    return 0


def cmd_project_link_skill(args: argparse.Namespace) -> int:
    registry = global_registry()
    project_identifier = args.project or str(TrailWorkspace.discover().root)
    skill, project = registry.link_skill_project(args.skill_name, project_identifier)
    _print_json({"skill": skill, "project": project})
    return 0


def _default_agent_slug_for_skill(skill_name: str) -> str:
    return f"{skill_name}-lead"


def _bootstrap_project_skill_agent(
    workspace: TrailWorkspace,
    *,
    skill_name: str,
    agent_name: str | None = None,
) -> dict:
    registry = global_registry()
    project = registry.upsert_project(workspace.root)
    skill = registry.upsert_skill(skill_name)
    skill, project = registry.link_skill_project(skill_name, project["slug"])

    chosen_agent_name = agent_name or _default_agent_slug_for_skill(skill_name)
    agent = registry.upsert_agent(
        name=chosen_agent_name,
        role="lead",
        description=f"Specialist agent for {skill_name} on {project['slug']}",
        system_prompt=(
            f"Operate as the lead specialist for skill {skill_name}. "
            "Be strong on exact project state, blockers, delivery risk, next steps, and knowledge recall. "
            "Use Trail before making assumptions."
        ),
    )
    agent = registry.link_agent(agent["slug"], project_identifier=project["slug"], skill_identifier=skill["slug"])

    return {"project": project, "skill": skill, "agent": agent}


def cmd_attach(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    records = _bootstrap_project_skill_agent(workspace, skill_name=args.skill_name, agent_name=args.agent)
    if args.goal:
        emit_event(
            workspace,
            session_id=_manual_session_id(workspace),
            kind="goal_set",
            payload={"goal": args.goal},
        )
    if args.next_step:
        record_next_step(workspace, summary=args.next_step)
    reduce_state(workspace)
    build_context_pack(workspace, skill_name=args.skill_name, user_task=args.goal)
    _print_json(records)
    return 0


def cmd_work(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    records = _bootstrap_project_skill_agent(workspace, skill_name=args.skill_name, agent_name=args.agent)
    task = " ".join(args.task).strip() or None

    # If an agent is requested, prefer the agent prompt. Otherwise use the skill prompt.
    if args.use_agent:
        agent = records["agent"]
        state = load_state(workspace)
        prompt = _agent_prompt(agent, workspace, state, task)
        if args.dry_run:
            print(prompt)
            return 0
        run_args = argparse.Namespace(
            goal=task or state.get("current_goal"),
            command=["codex", prompt],
            skill_name=args.skill_name,
            bootstrap=False,
        )
        return cmd_run(run_args)

    skill_args = argparse.Namespace(
        skill_name=args.skill_name,
        task=args.task,
        dry_run=args.dry_run,
    )
    return cmd_skill_run(skill_args)


def cmd_migration_setup(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    result = setup_migration_pack(
        workspace,
        business_rules=args.business_rules,
        conventions=args.conventions,
        gaps=args.gaps,
        flows=args.flows,
        skill_name=args.skill_name,
        agent_name=args.agent,
    )
    if args.goal:
        emit_event(
            workspace,
            session_id=_manual_session_id(workspace),
            kind="goal_set",
            payload={"goal": args.goal},
        )
    if args.next_step:
        record_next_step(workspace, summary=args.next_step)
    reduce_state(workspace)
    build_context_pack(workspace, skill_name=args.skill_name, user_task=args.goal)
    _print_json(result)
    return 0


def cmd_migration_prompt(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    task = " ".join(args.task).strip() or None
    print(build_migration_prompt(workspace, user_task=task))
    return 0


def cmd_migration_run(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    task = " ".join(args.task).strip() or None
    prompt = build_migration_prompt(workspace, user_task=task)

    if args.dry_run:
        print(prompt)
        return 0

    state = load_state(workspace)
    config = load_migration_pack(workspace) or {}
    run_args = argparse.Namespace(
        goal=task or state.get("current_goal"),
        command=["codex", prompt],
        skill_name=config.get("skill_name"),
        bootstrap=False,
    )
    return cmd_run(run_args)


def _agent_prompt(agent: dict, workspace: TrailWorkspace, state: dict, user_task: str | None) -> str:
    lines = [
        f"You are the specialized Trail agent `{agent.get('title')}`.",
        f"Role: {agent.get('role') or 'specialist'}",
    ]
    if agent.get("description"):
        lines.append(f"Description: {agent['description']}")
    lines.extend(
        [
            "",
            "Trail agent context:",
            f"- Project root: {workspace.root}",
            f"- Active goal: {state.get('current_goal') or 'No active goal recorded.'}",
            f"- Next step: {state.get('next_step') or 'No next step recorded.'}",
            f"- Open blockers: {len(state.get('open_blockers') or [])}",
            f"- Linked skills: {', '.join(agent.get('linked_skills') or []) or 'none'}",
            f"- Linked conversations: {', '.join(agent.get('linked_conversations') or []) or 'none'}",
        ]
    )
    if agent.get("system_prompt"):
        lines.extend(["", "Agent instructions:", agent["system_prompt"]])
    lines.extend(
        [
            "",
            "Trail Usage:",
            "- Fetch current Trail context first.",
            "- Fetch linked skill context when relevant.",
            "- Review linked conversations when history matters.",
            "- Record decisions, blockers, and next steps back into Trail.",
        ]
    )
    lines.extend(["", "User task:", user_task or "Confirm the goal and proceed using Trail context."])
    return "\n".join(lines) + "\n"


def cmd_agent_list(args: argparse.Namespace) -> int:
    registry = global_registry()
    _print_json({"items": registry.list_agents()})
    return 0


def cmd_agent_add(args: argparse.Namespace) -> int:
    registry = global_registry()
    record = registry.upsert_agent(
        name=args.name,
        role=args.role,
        description=args.description,
        system_prompt=args.system_prompt,
    )
    _print_json(record)
    return 0


def cmd_agent_show(args: argparse.Namespace) -> int:
    registry = global_registry()
    record = registry.get_agent(args.agent)
    if not record:
        raise SystemExit(f"Agent not found: {args.agent}")
    _print_json(record)
    return 0


def cmd_agent_link(args: argparse.Namespace) -> int:
    registry = global_registry()
    record = registry.link_agent(
        args.agent,
        project_identifier=args.project,
        skill_identifier=args.skill,
        conversation_identifier=args.conversation,
    )
    _print_json(record)
    return 0


def cmd_agent_run(args: argparse.Namespace) -> int:
    registry = global_registry()
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    registry.upsert_project(workspace.root)
    agent = registry.get_agent(args.agent)
    if not agent:
        raise SystemExit(f"Agent not found: {args.agent}")

    state = load_state(workspace)
    task = " ".join(args.task).strip() or None
    prompt = _agent_prompt(agent, workspace, state, task)

    if args.dry_run:
        print(prompt)
        return 0

    # If the agent has linked skills, use the first one as the active skill for the run.
    skill_name = None
    linked_skills = agent.get("linked_skills") or []
    if linked_skills:
        skill_name = linked_skills[0].replace("skill_", "").replace("_", "-")

    run_args = argparse.Namespace(
        goal=task or state.get("current_goal"),
        command=["codex", prompt],
        skill_name=skill_name,
        bootstrap=False,
    )
    return cmd_run(run_args)


def cmd_convo_list(args: argparse.Namespace) -> int:
    registry = global_registry()
    items = registry.list_conversations()
    if args.project:
        project = registry.get_project(args.project)
        project_id = project["id"] if project else args.project
        items = [item for item in items if item.get("project_id") == project_id]
    if args.skill:
        skill = registry.get_skill(args.skill)
        skill_id = skill["id"] if skill else args.skill
        items = [item for item in items if skill_id in (item.get("skill_ids") or [])]
    _print_json({"items": items})
    return 0


def cmd_convo_show(args: argparse.Namespace) -> int:
    registry = global_registry()
    workspace = TrailWorkspace.discover()
    identifier = args.conversation or (workspace.read_json(workspace.current_conversation_path) or {}).get("id")
    if not identifier:
        raise SystemExit("No conversation specified and no current local conversation.")
    record = registry.get_conversation(identifier)
    if not record:
        raise SystemExit(f"Conversation not found: {identifier}")
    _print_json(record)
    return 0


def cmd_convo_save(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    registry = global_registry()
    current = workspace.read_json(workspace.current_conversation_path)
    if not current:
        raise SystemExit("No current local conversation to save.")
    record = registry.upsert_conversation({**current, "root": str(workspace.root)})
    _print_json(record)
    return 0


def cmd_convo_fetch(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    conversation = fetch_conversation_to_workspace(workspace, args.conversation)
    _print_json(conversation)
    return 0


def cmd_skill_run(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover()
    init_workspace(workspace)
    state = load_state(workspace)
    skill = resolve_skill(args.skill_name)
    user_task = " ".join(args.task).strip() or None
    prompt = build_skill_briefing(workspace, skill, state, user_task)
    prompt += "\nTrail MCP tools are attached in this session.\n"

    emit_event(
        workspace,
        session_id=_manual_session_id(workspace),
        kind="skill_started",
        payload={"skill": skill.name, "task": user_task, "skill_path": str(skill.path)},
    )

    if args.dry_run:
        print(prompt)
        return 0

    run_args = argparse.Namespace(
        goal=user_task or state.get("current_goal"),
        command=["codex", prompt],
        skill_name=skill.name,
        bootstrap=False,
    )
    exit_code = cmd_run(run_args)
    emit_event(
        workspace,
        session_id=_manual_session_id(workspace),
        kind="skill_finished",
        payload={"skill": skill.name, "task": user_task, "exit_code": exit_code},
    )
    reduce_state(workspace)
    return exit_code


def cmd_mcp(args: argparse.Namespace) -> int:
    workspace = TrailWorkspace.discover(Path(os.environ.get("TRAIL_PROJECT_ROOT", Path.cwd())))
    init_workspace(workspace)
    run_stdio_server(workspace)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trail", description="Persistent work context for Codex")
    subparsers = parser.add_subparsers(dest="command", required=False)

    init_parser = subparsers.add_parser("init", help="Initialize .trail in the current repo")
    init_parser.add_argument("path", nargs="?", help="Optional directory to initialize")
    init_parser.set_defaults(func=cmd_init)

    attach_parser = subparsers.add_parser("attach", help="Bootstrap the current repo with a skill and default specialist agent")
    attach_parser.add_argument("skill_name")
    attach_parser.add_argument("--agent", help="Optional agent name; defaults to <skill>-lead")
    attach_parser.add_argument("--goal")
    attach_parser.add_argument("--next-step")
    attach_parser.set_defaults(func=cmd_attach)

    work_parser = subparsers.add_parser("work", help="Open Codex with Trail already attached for a skill")
    work_parser.add_argument("skill_name")
    work_parser.add_argument("task", nargs="*")
    work_parser.add_argument("--agent", help="Optional agent name; defaults to <skill>-lead")
    work_parser.add_argument("--use-agent", action="store_true", help="Use the specialist agent prompt instead of the raw skill prompt")
    work_parser.add_argument("--dry-run", action="store_true")
    work_parser.set_defaults(func=cmd_work)

    run_parser = subparsers.add_parser("run", help="Wrap an interactive Codex command")
    run_parser.add_argument("--goal", help="Record the current working goal")
    run_parser.add_argument("--bootstrap", action="store_true", help="Append a bootstrap prompt telling Codex to use Trail MCP")
    run_parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run, defaults to codex")
    run_parser.set_defaults(func=cmd_run)

    status_parser = subparsers.add_parser("status", help="Show current Trail state")
    status_parser.add_argument("--brief", action="store_true", help="Compact status view")
    status_parser.add_argument("--manager", action="store_true", help="Manager-ready status view")
    status_parser.set_defaults(func=cmd_status)

    checkpoint_parser = subparsers.add_parser("checkpoint", help="Create a state snapshot")
    checkpoint_parser.add_argument("--label", help="Optional checkpoint label")
    checkpoint_parser.set_defaults(func=cmd_checkpoint)

    handoff_parser = subparsers.add_parser("handoff", help="Create a human and JSON handoff")
    handoff_parser.add_argument("--label", help="Optional handoff label")
    handoff_parser.set_defaults(func=cmd_handoff)

    note_parser = subparsers.add_parser("note", help="Record structured project facts")
    note_subparsers = note_parser.add_subparsers(dest="note_command", required=True)

    note_goal_parser = note_subparsers.add_parser("goal", help="Record the current goal")
    note_goal_parser.add_argument("goal")
    note_goal_parser.set_defaults(func=cmd_note_goal)

    note_next_parser = note_subparsers.add_parser("next-step", help="Record the next step")
    note_next_parser.add_argument("summary")
    note_next_parser.set_defaults(func=cmd_note_next_step)

    note_decision_parser = note_subparsers.add_parser("decision", help="Record a decision")
    note_decision_parser.add_argument("summary")
    note_decision_parser.add_argument("--reason")
    note_decision_parser.add_argument("--impact")
    note_decision_parser.set_defaults(func=cmd_note_decision)

    note_blocker_parser = note_subparsers.add_parser("blocker", help="Record an open blocker")
    note_blocker_parser.add_argument("summary")
    note_blocker_parser.add_argument("--id")
    note_blocker_parser.add_argument("--severity")
    note_blocker_parser.add_argument("--owner")
    note_blocker_parser.add_argument("--workaround")
    note_blocker_parser.set_defaults(func=cmd_note_blocker)

    note_unblock_parser = note_subparsers.add_parser("unblock", help="Resolve a blocker by id")
    note_unblock_parser.add_argument("id")
    note_unblock_parser.set_defaults(func=cmd_note_unblock)

    note_doc_parser = note_subparsers.add_parser("doc", help="Record doc facts")
    note_doc_parser.add_argument("topic")
    note_doc_parser.add_argument("--source", required=True)
    note_doc_parser.add_argument("--fact", action="append")
    note_doc_parser.set_defaults(func=cmd_note_doc)

    note_spec_parser = note_subparsers.add_parser("spec", help="Record spec facts")
    note_spec_parser.add_argument("topic")
    note_spec_parser.add_argument("--source", required=True)
    note_spec_parser.add_argument("--fact", action="append")
    note_spec_parser.set_defaults(func=cmd_note_spec)

    skill_parser = subparsers.add_parser("skill", help="Run a Codex skill with Trail context")
    skill_subparsers = skill_parser.add_subparsers(dest="skill_command", required=True)

    skill_list_parser = skill_subparsers.add_parser("list", help="List registered Trail skills")
    skill_list_parser.set_defaults(func=cmd_skill_list)

    skill_add_parser = skill_subparsers.add_parser("add", help="Register a skill in the global Trail library")
    skill_add_parser.add_argument("skill_name")
    skill_add_parser.set_defaults(func=cmd_skill_add)

    skill_run_parser = skill_subparsers.add_parser("run", help="Launch Codex with a skill briefing")
    skill_run_parser.add_argument("skill_name")
    skill_run_parser.add_argument("task", nargs="*", help="Optional user task for the skill")
    skill_run_parser.add_argument("--dry-run", action="store_true", help="Print the generated prompt only")
    skill_run_parser.set_defaults(func=cmd_skill_run)

    skill_show_parser = skill_subparsers.add_parser("show", help="Show a resolved skill path")
    skill_show_parser.add_argument("skill_name")
    skill_show_parser.set_defaults(func=cmd_skill_show)

    skill_link_parser = skill_subparsers.add_parser("link", help="Link a skill to a project in the global Trail library")
    skill_link_parser.add_argument("skill_name")
    skill_link_parser.add_argument("project")
    skill_link_parser.set_defaults(func=cmd_skill_link)

    project_parser = subparsers.add_parser("project", help="Manage Trail project records")
    project_subparsers = project_parser.add_subparsers(dest="project_command", required=True)

    project_init_parser = project_subparsers.add_parser("init", help="Register the current repo as a Trail project")
    project_init_parser.add_argument("path", nargs="?")
    project_init_parser.add_argument("--title")
    project_init_parser.add_argument("--slug")
    project_init_parser.set_defaults(func=cmd_project_init)

    project_list_parser = project_subparsers.add_parser("list", help="List registered Trail projects")
    project_list_parser.set_defaults(func=cmd_project_list)

    project_show_parser = project_subparsers.add_parser("show", help="Show a registered Trail project")
    project_show_parser.add_argument("project", nargs="?")
    project_show_parser.set_defaults(func=cmd_project_show)

    project_link_skill_parser = project_subparsers.add_parser("link-skill", help="Link a skill to a Trail project")
    project_link_skill_parser.add_argument("skill_name")
    project_link_skill_parser.add_argument("project", nargs="?")
    project_link_skill_parser.set_defaults(func=cmd_project_link_skill)

    convo_parser = subparsers.add_parser("convo", help="Manage Trail conversation records")
    convo_subparsers = convo_parser.add_subparsers(dest="convo_command", required=True)

    convo_list_parser = convo_subparsers.add_parser("list", help="List registered Trail conversations")
    convo_list_parser.add_argument("--project")
    convo_list_parser.add_argument("--skill")
    convo_list_parser.set_defaults(func=cmd_convo_list)

    convo_show_parser = convo_subparsers.add_parser("show", help="Show a registered Trail conversation")
    convo_show_parser.add_argument("conversation", nargs="?")
    convo_show_parser.set_defaults(func=cmd_convo_show)

    convo_save_parser = convo_subparsers.add_parser("save", help="Save the current local conversation into the global Trail library")
    convo_save_parser.set_defaults(func=cmd_convo_save)

    convo_fetch_parser = convo_subparsers.add_parser("fetch", help="Fetch a global Trail conversation into the local repo workspace")
    convo_fetch_parser.add_argument("conversation")
    convo_fetch_parser.set_defaults(func=cmd_convo_fetch)

    agent_parser = subparsers.add_parser("agent", help="Manage Trail specialist agents")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command", required=True)

    agent_list_parser = agent_subparsers.add_parser("list", help="List registered Trail agents")
    agent_list_parser.set_defaults(func=cmd_agent_list)

    agent_add_parser = agent_subparsers.add_parser("add", help="Create or update a specialist agent")
    agent_add_parser.add_argument("name")
    agent_add_parser.add_argument("--role")
    agent_add_parser.add_argument("--description")
    agent_add_parser.add_argument("--system-prompt")
    agent_add_parser.set_defaults(func=cmd_agent_add)

    agent_show_parser = agent_subparsers.add_parser("show", help="Show a registered Trail agent")
    agent_show_parser.add_argument("agent")
    agent_show_parser.set_defaults(func=cmd_agent_show)

    agent_link_parser = agent_subparsers.add_parser("link", help="Link an agent to a project, skill, or conversation")
    agent_link_parser.add_argument("agent")
    agent_link_parser.add_argument("--project")
    agent_link_parser.add_argument("--skill")
    agent_link_parser.add_argument("--conversation")
    agent_link_parser.set_defaults(func=cmd_agent_link)

    agent_run_parser = agent_subparsers.add_parser("run", help="Run Codex as a specialized Trail agent")
    agent_run_parser.add_argument("agent")
    agent_run_parser.add_argument("task", nargs="*")
    agent_run_parser.add_argument("--dry-run", action="store_true")
    agent_run_parser.set_defaults(func=cmd_agent_run)

    migration_parser = subparsers.add_parser("migration", help="Bootstrap and run a migration audit pack")
    migration_subparsers = migration_parser.add_subparsers(dest="migration_command", required=True)

    migration_setup_parser = migration_subparsers.add_parser(
        "setup",
        help="Import migration audit docs, create the migration auditor agent, and store the pack locally",
    )
    migration_setup_parser.add_argument("skill_name", nargs="?")
    migration_setup_parser.add_argument("--business-rules", default="business_rules.md")
    migration_setup_parser.add_argument("--conventions", default="eui21_ecl21_conventions.md")
    migration_setup_parser.add_argument("--gaps", default="migration_gaps.md")
    migration_setup_parser.add_argument("--flows", default="critical_flows.md")
    migration_setup_parser.add_argument("--agent", default="migration-auditor")
    migration_setup_parser.add_argument("--goal")
    migration_setup_parser.add_argument("--next-step")
    migration_setup_parser.set_defaults(func=cmd_migration_setup)

    migration_prompt_parser = migration_subparsers.add_parser(
        "prompt",
        help="Print the migration audit prompt built from the local pack",
    )
    migration_prompt_parser.add_argument("task", nargs="*")
    migration_prompt_parser.set_defaults(func=cmd_migration_prompt)

    migration_run_parser = migration_subparsers.add_parser(
        "run",
        help="Open Codex with the migration audit prompt and Trail MCP attached",
    )
    migration_run_parser.add_argument("task", nargs="*")
    migration_run_parser.add_argument("--dry-run", action="store_true")
    migration_run_parser.set_defaults(func=cmd_migration_run)

    mcp_parser = subparsers.add_parser("mcp", help="Run the Trail MCP stdio server")
    mcp_parser.set_defaults(func=cmd_mcp)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        return cmd_run(argparse.Namespace(goal=None, command=["codex"], skill_name=None, bootstrap=True))
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
