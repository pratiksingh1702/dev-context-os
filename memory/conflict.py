"""Conflict Detection Engine for Concurrent AI Agent / Developer Sessions.

Lifted and adapted from Context Gateway gateway/core/memory/conflict_detector.py.
Computes file set intersection: set(current_files) & set(other_session.files_accessed).
Extracts stated intent and assigns domain risk levels.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from memory.store import MemoryStore

SENSITIVE_PATHS = ["auth", "payment", "security", "core", "database", "crypto"]


@dataclass
class ConflictWarning:
    file_path: str
    colliding_session_id: str
    agent_name: str
    developer_name: str
    stated_intent: str
    risk_level: str  # 'HIGH' | 'MEDIUM'
    started_at: str


class ConflictDetector:
    def __init__(self, store: MemoryStore | None = None):
        self.store = store or MemoryStore()

    def detect_conflicts(
        self,
        touched_files: list[str],
        current_session_id: str | None = None,
    ) -> list[ConflictWarning]:
        """Checks if touched files intersect with other in-progress sessions."""
        active_sessions = self.store.get_active_sessions()
        conflicts: list[ConflictWarning] = []
        current_file_set = {f.replace("\\", "/").strip("/") for f in touched_files}

        for sess in active_sessions:
            if current_session_id and sess["session_id"] == current_session_id:
                continue

            sess_file_set = {f.replace("\\", "/").strip("/") for f in sess["files_accessed"]}
            overlap = current_file_set & sess_file_set

            for overlapped_file in overlap:
                # Assess domain risk
                risk = "MEDIUM"
                for sensitive in SENSITIVE_PATHS:
                    if sensitive in overlapped_file.lower():
                        risk = "HIGH"
                        break

                conflicts.append(
                    ConflictWarning(
                        file_path=overlapped_file,
                        colliding_session_id=sess["session_id"],
                        agent_name=sess["agent_name"],
                        developer_name=sess["developer_name"],
                        stated_intent=sess["stated_intent"],
                        risk_level=risk,
                        started_at=sess["started_at"],
                    )
                )

        return conflicts
