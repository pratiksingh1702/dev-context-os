-- SQLite Schema for AI Developer Context OS

CREATE TABLE IF NOT EXISTS memory_entries (
    entry_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL, -- 'adr', 'bug_fix', 'architecture', 'decision'
    content TEXT NOT NULL,
    affected_files TEXT, -- JSON array of file paths e.g. ["core/auth.py"]
    source_tool TEXT DEFAULT 'user', -- 'claude_code', 'codex', 'cursor', 'user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS active_sessions (
    session_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL, -- 'claude_code', 'codex', 'cursor'
    developer_name TEXT NOT NULL,
    task_description TEXT NOT NULL,
    stated_intent TEXT NOT NULL, -- "Why this change is being made"
    files_accessed TEXT NOT NULL, -- JSON array of file paths
    status TEXT NOT NULL DEFAULT 'in_progress', -- 'in_progress', 'completed', 'aborted'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file_locks (
    file_path TEXT PRIMARY KEY,
    locked_by_session TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conflict_events (
    event_id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    pushing_session_id TEXT,
    colliding_session_id TEXT NOT NULL,
    risk_level TEXT NOT NULL, -- 'high', 'medium', 'low'
    intent_a TEXT NOT NULL,
    intent_b TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
