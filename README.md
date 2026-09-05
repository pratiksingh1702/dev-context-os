# AI Developer Context OS (`dev-context-os`)
### Persistent Multi-Tool Project Memory & Conflict-Aware Git Interceptor
**Razorpay AI Buildathon 2026 — Open Track Submission**  
**Builder:** Pratik Singh · NIT Jalandhar · ECE '27 · [GitHub Profile](https://github.com/pratiksingh1702)

[![CI Tests](https://img.shields.io/badge/pytest-4%20passed-brightgreen)](#)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](#)
[![Protocol](https://img.shields.io/badge/protocol-MCP%20JSON--RPC%202.0-orange)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](#)

---

## 1. Problem Statement & The "Why Now"

When autonomous AI coding agents (Claude Code, Cursor, Codex, Windsurf) work concurrently alongside human developers, software development hits two critical bottlenecks:

1. **Context Amnesia Across Tools:** Switching between Claude Code, Cursor, and Codex wipes out all memory of past resolved bug fixes, architectural guidelines, and security policies. Each agent begins from zero.
2. **Silent Multi-Agent Git Collisions:** Git only understands line differences after the fact. When two agents modify overlapping files concurrently, conflicts are discovered only *after* pushes succeed, creating merge deadlocks and broken CI builds.

**AI Developer Context OS** provides:
* **Persistent Project Memory:** Zero-config SQLite WAL store retaining ADRs, bug fixes, and guidelines.
* **Hard Token Budget Compression:** Powered by `tiktoken` (`cl100k_base`) to guarantee memory injections never blow LLM context limits.
* **Instantaneous Git Interception:** A sub-12ms Git pre-push hook that intercepts concurrent pushes and presents the other agent's **stated human-readable intent** before code is overwritten.
* **Model Context Protocol (MCP) Stdio Server:** Native integration with Cursor, Claude Desktop, Claude Code, and Windsurf.

---

## 2. Architecture & AI Judgment

Razorpay evaluation pillar: *The right tool in the right place, and where you chose not to use one.*

```
AI Coding Clients (Claude Desktop / Cursor / Windsurf / Claude Code)
 │
 ├── 1. memoryctl remember ────────────────► SQLite Persistent Memory (~/.contextos/memory.db)
 │      (Store ADRs, bug fixes, decisions)
 │
 ├── 2. memoryctl recall ──────────────────► Semantic Search + Token Budget Compression
 │      (Retrieve past context within budget)
 │
 ├── 3. MCP Server (mcp/server.py) ────────► Native JSON-RPC 2.0 Tool Protocol
 │
 └── 4. git push (Pre-Push Hook) ──────────► Deterministic Conflict Interceptor
        │
        ├── Mathematical Set Intersection: set(pushed_files) ∩ set(active_session_files)
        ├── Domain Risk Classification: (HIGH for auth/payment/core)
        └── Rich Terminal Warning with Concurrent Agent's Stated Intent (< 12ms)
```

### Why We Did NOT Use an LLM for Conflict Interception
* Intercepting `git push` requires **absolute determinism, zero hallucinations, and sub-50ms latency**.
* Passing commit diffs to an LLM or neural embedder on every `git push` introduces 4–8 seconds of latency and non-deterministic false positives.
* Instead, we use **pure mathematical set intersection ($O(1)$)** in SQLite for safety, reserving AI embeddings and LLM reasoning strictly for semantic recall and summarization.

---

## 3. Quickstart (30 Seconds to Run)

### 1. Installation
```bash
# Clone repository
git clone https://github.com/pratiksingh1702/dev-context-os.git
cd dev-context-os

# Install dependencies in editable mode
pip install -e .
```

### 2. Run Automated Verification Tests
```bash
pytest tests
```
*Output: `4 passed in 0.50s`.*

### 3. Run Live Multi-Agent Collision Demo
```bash
python demo/simulate_collision.py
```

---

## 4. Production CLI Usage (`memoryctl`)

### Install Git Hook into Any Repository
```bash
memoryctl install-hook --repo .
```

### Store an Architectural Decision or Bug Resolution
```bash
memoryctl remember "Fixed JWT expiration race condition by adding 30s leeway buffer" --category bug_fix --file core/auth.py
```

### Recall Past Project Memory (Within Exact Token Budget)
```bash
memoryctl recall "auth race condition" --budget 300
```
*Output:*
```
• [BUG_FIX] JWT Token Expiry Race Condition Fix
  Resolved intermittent 401 Unauthorized under high concurrency by introducing a 30-second leeway buffer and Redis-backed refresh mutex in core/auth.py.
  Files: core/auth.py, core/security/jwt.py

Tokens Used: 70 / 300 | Tokens Saved: 142
```

### Register Active AI Agent Session
```bash
memoryctl session-start --agent claude_code --dev "Pratik" --intent "Refactoring token validation loop to eliminate deadlock" --file core/auth.py
```

### Check Active Sessions & Stored Memories
```bash
memoryctl status
```

### Test Git Pre-Push Interceptor
```bash
memoryctl check-conflicts core/auth.py
```
*Output (Returns exit code 1 to halt Git push):*
```
[!] CONCURRENT EDIT WARNING DETECTED BEFORE PUSH
One or more files in this push are currently being modified by another active AI session.

• File: core/auth.py (Risk: HIGH)
  ├── Active Agent: claude_code (Pratik Singh)
  ├── Stated Intent: "Refactoring token validation loop to eliminate deadlock"
  └── Started At: 2026-09-05 17:29:03

Suggested Action: Review the active session's intent or rebase before overwriting.
```

---

## 5. Model Context Protocol (MCP) Setup

Add Context OS as an MCP server to **Cursor** (`.cursor/mcp.json`) or **Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "context-os": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "env": {}
    }
  }
}
```

### Exposed MCP Tools
1. `context_remember`: Persist ADRs and bug resolutions into SQLite memory.
2. `context_recall`: Retrieve past project decisions within strict token budgets.
3. `context_session_start`: Soft-lock files and register agent intent.
4. `context_session_end`: Release file reservations upon task completion.
5. `context_check_conflicts`: Inspect active file touch-sets before generating code.

---

## 6. What Broke, and How We Got Out of It

*(Razorpay evaluation note: "The last one is the one we read first.")*

Read the full 5-failure technical postmortem in [`WHAT_BROKE.md`](WHAT_BROKE.md):
1. **Pre-Push Hook Latency Spike (6.2s Freeze):** Replaced synchronous neural embeddings over diffs with asynchronous agent intent registration + $O(1)$ SQLite set intersection (< 12ms latency).
2. **Context Window Bloat & Starvation:** Replaced raw top-$k$ memory dumping with `tiktoken` knapsack budget compression.
3. **SQLite Concurrency Contention:** Resolved `sqlite3.OperationalError: database is locked` across parallel agent workers by enabling Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and 5,000ms busy timeouts.
4. **Cross-Platform Git Hook Shell Drift:** Resolved Windows MSYS bash path-splitting failures using POSIX path normalization and fallback runners.
5. **Orphaned Locks from Crashed Agents:** Implemented soft session TTL leases and immediate `--no-verify` safety bypasses.

---

## 7. Submission Artifacts

* **Pitch Video Guide:** See [`VIDEO_SCRIPT_AND_COMMANDS.txt`](VIDEO_SCRIPT_AND_COMMANDS.txt) for the second-by-second 5-minute video presentation flow.
* **Engineering Postmortem:** [`WHAT_BROKE.md`](WHAT_BROKE.md)
* **Single-Command Git Repo Setup:** Run `powershell ./setup_git.ps1` or `bash ./setup_git.sh`
