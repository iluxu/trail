from __future__ import annotations

import json
import os
import sys
from typing import Any

from .audit import record_finding
from .operations import (
    build_context_pack,
    build_startup_brief,
    create_handoff,
    get_registered_conversation,
    list_project_conversations,
    load_state,
    record_blocker,
    record_decision,
    record_next_step,
    search_knowledge,
)
from .overlay import build_skill_overlay
from .packs import list_packs, load_pack
from .reporting import build_manager_report, build_risk_register
from .workspace import TrailWorkspace


DEFAULT_PROTOCOL_VERSION = "2024-11-05"


def _jsonrpc_result(result: Any, req_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(code: int, message: str, req_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "trail_get_startup_brief",
            "description": "Call this immediately at session start when Codex was launched by Trail. It returns the active skill, agent, migration pack, and the next Trail calls to make.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "trail_get_current_context",
            "description": "Return the current Trail context pack for this project/session. Call this before making project-state assumptions.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "trail_get_skill_context",
            "description": "Return Trail context and briefing for a specific skill. Call this before deep work with a known skill.",
            "inputSchema": {
                "type": "object",
                "properties": {"skill": {"type": "string", "description": "Skill slug, e.g. rag-docs-api"}},
                "required": [],
            },
        },
        {
            "name": "trail_get_skill_overlay",
            "description": "Return the dynamic local overlay for a skill. Call this when project-specific conventions or active packs may matter.",
            "inputSchema": {
                "type": "object",
                "properties": {"skill": {"type": "string", "description": "Optional skill slug"}},
                "required": [],
            },
        },
        {
            "name": "trail_list_packs",
            "description": "List active local project packs. Call this when Trail may have imported audit, domain, or project packs shaping the current task.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "trail_get_manager_report",
            "description": "Return a manager-ready project report built from Trail state. Call this when the user asks for status, risks, progress, or next steps.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "trail_get_risk_register",
            "description": "Return the current Trail risk register. Call this when prioritizing risks, blockers, audit gaps, or runtime concerns.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "trail_search_knowledge",
            "description": "Search retained Trail knowledge and linked skill files. Call this before answering doc/spec questions from memory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "skill": {"type": "string", "description": "Optional skill slug"},
                    "limit": {"type": "integer", "description": "Maximum number of results"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "trail_list_project_conversations",
            "description": "List recent Trail conversations for a project. Call this when prior work may matter for the current task.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Optional project slug or id"},
                    "limit": {"type": "integer", "description": "Maximum number of conversations"},
                },
                "required": [],
            },
        },
        {
            "name": "trail_fetch_conversation",
            "description": "Fetch one Trail conversation by id. Call this when you need specific prior context instead of guessing.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string", "description": "Conversation id, e.g. conv_abc123"}
                },
                "required": ["conversation_id"],
            },
        },
        {
            "name": "trail_record_decision",
            "description": "Record an important decision in Trail. Call this after architectural or workflow decisions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "reason": {"type": "string"},
                    "impact": {"type": "string"},
                },
                "required": ["summary"],
            },
        },
        {
            "name": "trail_record_finding",
            "description": "Record an audit or review finding in Trail. Call this when you confirm a gap, risk, compliance issue, or needs-verification item.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "severity": {"type": "string"},
                    "status": {"type": "string"},
                    "category": {"type": "string"},
                    "source": {"type": "string"},
                    "evidence": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
                "required": ["summary"],
            },
        },
        {
            "name": "trail_record_blocker",
            "description": "Record an open blocker in Trail. Call this when you discover something that blocks progress.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "id": {"type": "string"},
                    "severity": {"type": "string"},
                    "owner": {"type": "string"},
                    "workaround": {"type": "string"},
                },
                "required": ["summary"],
            },
        },
        {
            "name": "trail_record_next_step",
            "description": "Record the next best step in Trail. Call this when the next action becomes clear.",
            "inputSchema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        },
        {
            "name": "trail_save_handoff",
            "description": "Create a Trail handoff for the current session. Call this before ending or parking the task.",
            "inputSchema": {
                "type": "object",
                "properties": {"label": {"type": "string"}},
                "required": [],
            },
        },
    ]


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _content_response(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": _json_text(payload)}], "isError": is_error}


def _env_skill_slug() -> str | None:
    value = os.environ.get("TRAIL_SKILL_SLUG", "").strip()
    return value or None


def _call_tool(workspace: TrailWorkspace, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "trail_get_startup_brief":
        return build_startup_brief(workspace)

    if name == "trail_get_current_context":
        return build_context_pack(workspace)

    if name == "trail_get_skill_context":
        skill_name = arguments.get("skill") or _env_skill_slug()
        if not skill_name:
            raise ValueError("trail_get_skill_context requires a skill argument or TRAIL_SKILL_SLUG")
        context = build_context_pack(workspace, skill_name=skill_name)
        return {
            "skill": skill_name,
            "project_id": context.get("project_id"),
            "conversation_id": context.get("conversation_id"),
            "briefing": context.get("briefing"),
            "open_blockers": context.get("open_blockers"),
            "recent_decisions": context.get("recent_decisions"),
            "recent_failures": context.get("recent_failures"),
        }

    if name == "trail_get_skill_overlay":
        skill_name = arguments.get("skill") or _env_skill_slug()
        if not skill_name:
            raise ValueError("trail_get_skill_overlay requires a skill argument or TRAIL_SKILL_SLUG")
        return {"overlay": build_skill_overlay(workspace, skill_name, state=load_state(workspace))}

    if name == "trail_list_packs":
        return {"items": list_packs(workspace)}

    if name == "trail_get_manager_report":
        return {"report": build_manager_report(workspace)}

    if name == "trail_get_risk_register":
        return {"risk_register": build_risk_register(workspace)}

    if name == "trail_search_knowledge":
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("trail_search_knowledge.query must be a non-empty string")
        skill_name = arguments.get("skill") or _env_skill_slug()
        limit = int(arguments.get("limit") or 5)
        return {"items": search_knowledge(workspace, query=query, skill_name=skill_name, limit=limit)}

    if name == "trail_list_project_conversations":
        limit = int(arguments.get("limit") or 10)
        project = arguments.get("project")
        return {"items": list_project_conversations(workspace, project_identifier=project, limit=limit)}

    if name == "trail_fetch_conversation":
        conversation_id = arguments.get("conversation_id")
        if not isinstance(conversation_id, str) or not conversation_id.strip():
            raise ValueError("trail_fetch_conversation.conversation_id must be a non-empty string")
        conversation = get_registered_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")
        return {"conversation": conversation}

    if name == "trail_record_decision":
        summary = arguments.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("trail_record_decision.summary must be a non-empty string")
        event = record_decision(
            workspace,
            summary=summary,
            reason=arguments.get("reason"),
            impact=arguments.get("impact"),
        )
        return {"ok": True, "event_id": event["id"]}

    if name == "trail_record_blocker":
        summary = arguments.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("trail_record_blocker.summary must be a non-empty string")
        event = record_blocker(
            workspace,
            summary=summary,
            blocker_id=arguments.get("id"),
            severity=arguments.get("severity"),
            owner=arguments.get("owner"),
            workaround=arguments.get("workaround"),
        )
        return {"ok": True, "event_id": event["id"]}

    if name == "trail_record_finding":
        summary = arguments.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("trail_record_finding.summary must be a non-empty string")
        event = record_finding(
            workspace,
            summary=summary,
            severity=arguments.get("severity"),
            status=arguments.get("status"),
            category=arguments.get("category"),
            source=arguments.get("source"),
            evidence=arguments.get("evidence"),
            recommendation=arguments.get("recommendation"),
        )
        return {"ok": True, "event_id": event["id"]}

    if name == "trail_record_next_step":
        summary = arguments.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("trail_record_next_step.summary must be a non-empty string")
        event = record_next_step(workspace, summary=summary)
        return {"ok": True, "event_id": event["id"]}

    if name == "trail_save_handoff":
        label = arguments.get("label") or "mcp-handoff"
        paths = create_handoff(workspace, label=label)
        return {
            "ok": True,
            "handoff": {"json_path": str(paths["json_path"]), "md_path": str(paths["md_path"])},
        }

    raise ValueError(f"Unknown tool: {name}")


def run_stdio_server(workspace: TrailWorkspace) -> None:
    tools = _tool_definitions()
    load_state(workspace)

    while True:
        raw = sys.stdin.buffer.readline()
        if not raw:
            return
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue

        try:
            message = json.loads(line)
        except Exception:
            continue

        req_id = message.get("id")
        if req_id is None:
            continue

        method = message.get("method")
        params = message.get("params") or {}

        try:
            if method == "initialize":
                protocol_version = params.get("protocolVersion") if isinstance(params, dict) else None
                payload = {
                    "protocolVersion": protocol_version or DEFAULT_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "trail", "version": "0.1.0"},
                }
                response = _jsonrpc_result(payload, req_id)
            elif method == "tools/list":
                response = _jsonrpc_result({"tools": tools}, req_id)
            elif method == "tools/call":
                if not isinstance(params, dict):
                    raise ValueError("tools/call params must be an object")
                tool_name = params.get("name")
                arguments = params.get("arguments") or {}
                if not isinstance(tool_name, str) or not tool_name:
                    raise ValueError("tools/call.name must be a non-empty string")
                if not isinstance(arguments, dict):
                    raise ValueError("tools/call.arguments must be an object")
                result = _call_tool(workspace, tool_name, arguments)
                response = _jsonrpc_result(_content_response(result), req_id)
            elif method == "resources/list":
                response = _jsonrpc_result({"resources": []}, req_id)
            elif method == "prompts/list":
                response = _jsonrpc_result({"prompts": []}, req_id)
            elif method == "ping":
                response = _jsonrpc_result({}, req_id)
            else:
                response = _jsonrpc_error(-32601, f"Method not found: {method}", req_id)
        except Exception as exc:
            response = _jsonrpc_result(_content_response({"error": str(exc)}, is_error=True), req_id)

        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
