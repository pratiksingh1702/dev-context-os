"""Model Context Protocol (MCP) Stdio Server for AI Developer Context OS.

Allows any AI coding client (Claude Desktop, Cursor, Claude Code, Windsurf, Roo Code)
to interact natively with persistent project memory and conflict detection.

Exposed MCP Tools:
- `context_remember`: Save ADRs / past bug fixes into project memory.
- `context_recall`: Retrieve past context with token budget limits.
- `context_session_start`: Register an active coding session on files.
- `context_session_end`: Conclude an active session.
- `context_check_conflicts`: Inspect active concurrent edits before generating code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Bootstrap project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.compressor import ContextCompressor
from memory.conflict import ConflictDetector
from memory.semantic import SemanticMemorySearch
from memory.store import MemoryStore

store = MemoryStore()
searcher = SemanticMemorySearch()
compressor = ContextCompressor()
conflict_detector = ConflictDetector(store)

TOOLS_METADATA = [
    {
        "name": "context_remember",
        "description": "Store an architectural decision record (ADR), resolved bug fix, or project guideline into persistent project memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short descriptive title"},
                "content": {"type": "string", "description": "The detailed resolution, architecture decision, or bug fix"},
                "category": {"type": "string", "enum": ["adr", "bug_fix", "architecture", "decision"], "default": "decision"},
                "affected_files": {"type": "array", "items": {"type": "string"}, "description": "File paths touched"},
                "tool_name": {"type": "string", "default": "ai_agent"}
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "context_recall",
        "description": "Retrieve relevant past architectural decisions and resolved bug fixes within a specified token budget.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for past project context"},
                "budget": {"type": "integer", "description": "Max token budget for returned context", "default": 800}
            },
            "required": ["query"]
        }
    },
    {
        "name": "context_session_start",
        "description": "Register an active AI coding session to lock touched files and avoid concurrent developer collisions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Name of AI agent or tool e.g. claude_code, cursor, codex"},
                "developer_name": {"type": "string", "description": "Name of the developer"},
                "task_description": {"type": "string", "description": "High level task summary"},
                "stated_intent": {"type": "string", "description": "Why these changes are being made"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "List of files being edited"}
            },
            "required": ["agent_name", "stated_intent", "files"]
        }
    },
    {
        "name": "context_session_end",
        "description": "Mark an AI coding session as finished and release all acquired file reservations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to terminate"}
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "context_check_conflicts",
        "description": "Check if a list of files is currently being modified by another developer or active AI session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {"type": "array", "items": {"type": "string"}, "description": "Files to check for collisions"}
            },
            "required": ["files"]
        }
    }
]


def handle_tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "context_remember":
        entry_id = store.add_memory(
            title=args["title"],
            category=args.get("category", "decision"),
            content=args["content"],
            affected_files=args.get("affected_files", []),
            source_tool=args.get("tool_name", "ai_agent"),
        )
        return {"content": [{"type": "text", "text": f"Successfully stored memory entry: {entry_id}"}]}

    elif name == "context_recall":
        all_mems = store.get_all_memories(limit=50)
        ranked = searcher.search(args["query"], all_mems, top_k=5)
        packed, used, saved = compressor.pack_memories(ranked, token_budget=args.get("budget", 800))
        summary = "\n\n".join([f"[{m['category'].upper()}] {m['title']}: {m['content']} (Files: {', '.join(m['affected_files'])})" for m in packed])
        return {"content": [{"type": "text", "text": summary or "No relevant project memory found."}]}

    elif name == "context_session_start":
        sess_id = store.start_session(
            agent_name=args["agent_name"],
            developer_name=args.get("developer_name", "Developer"),
            task_description=args.get("task_description", "Feature development"),
            stated_intent=args["stated_intent"],
            files_accessed=args["files"],
        )
        return {"content": [{"type": "text", "text": f"Active session registered: {sess_id} on {len(args['files'])} file(s)"}]}

    elif name == "context_session_end":
        store.end_session(args["session_id"])
        return {"content": [{"type": "text", "text": f"Session {args['session_id']} ended and locks released."}]}

    elif name == "context_check_conflicts":
        conflicts = conflict_detector.detect_conflicts(args["files"])
        if not conflicts:
            return {"content": [{"type": "text", "text": "No concurrent conflicts detected on specified files."}]}
        
        warns = [f"Conflict on {c.file_path}: Active Agent '{c.agent_name}' ({c.developer_name}) Intent: '{c.stated_intent}' [Risk: {c.risk_level}]" for c in conflicts]
        return {"content": [{"type": "text", "text": "\n".join(warns)}]}

    return {"error": f"Unknown tool: {name}"}


def main():
    """JSON-RPC 2.0 stdio server loop for MCP."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")

            if method == "tools/list":
                res = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_METADATA}}
            elif method == "tools/call":
                params = req.get("params", {})
                tool_res = handle_tool_call(params.get("name", ""), params.get("arguments", {}))
                res = {"jsonrpc": "2.0", "id": req_id, "result": tool_res}
            elif method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "ai-dev-context-os", "version": "1.0.0"}
                    }
                }
            else:
                res = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_res = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
