"""Unit tests for AI Developer Context OS."""

import pytest
from pathlib import Path
from memory.conflict import ConflictDetector
from memory.compressor import ContextCompressor
from memory.store import MemoryStore


def test_memory_store_and_conflict_detection(tmp_path: Path):
    db_path = tmp_path / "test_memory.db"
    store = MemoryStore(db_path=db_path)
    detector = ConflictDetector(store=store)
    compressor = ContextCompressor()

    # 1. Add Memory
    entry_id = store.add_memory(
        title="Test ADR",
        category="adr",
        content="Test content for database migration",
        affected_files=["db/migration.py"],
    )
    assert entry_id.startswith("mem_")
    assert len(store.get_all_memories()) == 1

    # 2. Start Active Session
    sess_id = store.start_session(
        agent_name="claude_code",
        developer_name="Pratik",
        task_description="Refactoring Auth",
        stated_intent="Updating auth tokens",
        files_accessed=["core/auth.py", "server/main.py"],
    )
    assert sess_id.startswith("sess_")
    assert len(store.get_active_sessions()) == 1

    # 3. Detect Conflict on Overlapping File
    conflicts = detector.detect_conflicts(["core/auth.py", "other/file.py"])
    assert len(conflicts) == 1
    assert conflicts[0].file_path == "core/auth.py"
    assert conflicts[0].risk_level == "HIGH"
    assert conflicts[0].stated_intent == "Updating auth tokens"

    # 4. Token Compression
    mems = store.get_all_memories()
    packed, used, saved = compressor.pack_memories(mems, token_budget=500)
    assert len(packed) == 1
    assert used > 0

    # 5. End Session
    store.end_session(sess_id)
    assert len(store.get_active_sessions()) == 0
    assert len(detector.detect_conflicts(["core/auth.py"])) == 0


def test_semantic_search():
    from memory.semantic import SemanticMemorySearch
    searcher = SemanticMemorySearch()
    memories = [
        {"title": "JWT Bug Fix", "content": "Fixed race condition with auth token leeway buffer", "category": "bug_fix"},
        {"title": "DB Optimization", "content": "Configured postgres connection pooling", "category": "adr"},
    ]
    results = searcher.search("authentication token race", memories, top_k=1)
    assert len(results) == 1
    assert "JWT" in results[0]["title"]


def test_mcp_tools():
    from mcp.server import handle_tool_call
    # Test context_remember tool
    res = handle_tool_call("context_remember", {
        "title": "MCP ADR",
        "content": "Using SQLite WAL mode",
        "category": "adr",
        "affected_files": ["memory/store.py"],
        "tool_name": "cursor",
    })
    assert "content" in res
    assert "Successfully stored" in res["content"][0]["text"]

    # Test context_recall tool
    recall_res = handle_tool_call("context_recall", {"query": "WAL mode", "budget": 400})
    assert "content" in recall_res
    assert len(recall_res["content"][0]["text"]) > 0


def test_conflict_interceptor_exit_code(tmp_path: Path):
    from hooks.interceptor import intercept_push
    store = MemoryStore(db_path=tmp_path / "intercept.db")
    
    # Clean state: push allowed (0)
    assert intercept_push(["file_a.py"]) == 0

    # Active session modifying file_a.py
    store.start_session(
        agent_name="codex",
        developer_name="Alex",
        task_description="DB migration",
        stated_intent="Updating migration script",
        files_accessed=["file_a.py"],
    )

    # With conflict active on file_a.py: push intercepted with exit code 1
    # Replace global store temporarily for test
    from hooks import interceptor
    interceptor.MemoryStore = lambda: store
    assert intercept_push(["file_a.py"]) == 1

