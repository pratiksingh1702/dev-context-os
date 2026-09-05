"""SQLite Storage Engine for AI Developer Context OS.

Manages:
- Persistent project memory entries (ADRs, past bug fixes, architectural guidelines).
- Active developer/AI agent sessions and concurrent file touch-sets.
- Soft file locking and conflict event logging.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path.home() / ".contextos" / "memory.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class MemoryStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            if SCHEMA_PATH.exists():
                with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            conn.commit()

    # =========================================================================
    # Memory Entries (ADRs, Bug Fixes, Decisions)
    # =========================================================================
    def add_memory(
        self,
        title: str,
        category: str,
        content: str,
        affected_files: list[str] | None = None,
        source_tool: str = "user",
    ) -> str:
        entry_id = f"mem_{uuid.uuid4().hex[:8]}"
        files_json = json.dumps(affected_files or [])
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memory_entries (entry_id, title, category, content, affected_files, source_tool)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (entry_id, title, category, content, files_json, source_tool),
            )
            conn.commit()
        return entry_id

    def get_all_memories(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT entry_id, title, category, content, affected_files, source_tool, created_at FROM memory_entries ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "entry_id": r["entry_id"],
                    "title": r["title"],
                    "category": r["category"],
                    "content": r["content"],
                    "affected_files": json.loads(r["affected_files"]),
                    "source_tool": r["source_tool"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    # =========================================================================
    # Active Sessions (Claude Code, Codex, Cursor)
    # =========================================================================
    def start_session(
        self,
        agent_name: str,
        developer_name: str,
        task_description: str,
        stated_intent: str,
        files_accessed: list[str],
    ) -> str:
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        files_json = json.dumps(files_accessed)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO active_sessions (session_id, agent_name, developer_name, task_description, stated_intent, files_accessed, status)
                VALUES (?, ?, ?, ?, ?, ?, 'in_progress')
                """,
                (session_id, agent_name, developer_name, task_description, stated_intent, files_json),
            )
            # Soft-lock touched files
            for fp in files_accessed:
                conn.execute(
                    "INSERT OR REPLACE INTO file_locks (file_path, locked_by_session, agent_name) VALUES (?, ?, ?)",
                    (fp, session_id, agent_name),
                )
            conn.commit()
        return session_id

    def end_session(self, session_id: str, status: str = "completed") -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE active_sessions SET status = ?, ended_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (status, session_id),
            )
            # Release file locks
            conn.execute("DELETE FROM file_locks WHERE locked_by_session = ?", (session_id,))
            conn.commit()

    def get_active_sessions(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id, agent_name, developer_name, task_description, stated_intent, files_accessed, started_at FROM active_sessions WHERE status = 'in_progress'"
            )
            rows = cursor.fetchall()
            return [
                {
                    "session_id": r["session_id"],
                    "agent_name": r["agent_name"],
                    "developer_name": r["developer_name"],
                    "task_description": r["task_description"],
                    "stated_intent": r["stated_intent"],
                    "files_accessed": json.loads(r["files_accessed"]),
                    "started_at": r["started_at"],
                }
                for r in rows
            ]

    def log_conflict(
        self,
        file_path: str,
        pushing_session_id: str | None,
        colliding_session_id: str,
        risk_level: str,
        intent_a: str,
        intent_b: str,
    ) -> str:
        event_id = f"conf_{uuid.uuid4().hex[:8]}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO conflict_events (event_id, file_path, pushing_session_id, colliding_session_id, risk_level, intent_a, intent_b)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, file_path, pushing_session_id, colliding_session_id, risk_level, intent_a, intent_b),
            )
            conn.commit()
        return event_id
