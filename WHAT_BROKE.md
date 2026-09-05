# Engineering Postmortem: What Broke, and How We Got Out of It
### Open Track: AI Developer Context OS (Razorpay AI Buildathon 2026)
**Builder:** Pratik Singh · NIT Jalandhar · ECE '27

---

## Executive Summary

When building an autonomous developer infrastructure tool, the cardinal rule is: **never get in the developer's way.**
Developers and autonomous AI coding agents (Claude Code, Cursor, Codex, Windsurf) move fast. If a tool introduces friction, latency, or false blocks, developers immediately bypass it (e.g., passing --no-verify on Git push).

During the architecture and end-to-end stress testing of **AI Developer Context OS**, we encountered 5 critical failure modes across real-time Git hooks, token budget compression, multi-agent concurrency, and cross-platform process isolation.

Here is what failed, the root cause analysis, and the exact engineering recovery for each.

---

## Failure Index

1. **Pre-Push Hook Latency Spike (6.2s Freeze):** Synchronous neural embeddings blocking git push.
2. **Context Window Bloat & Model Starvation:** Unbounded prompt injection exhausting agent context limits.
3. **SQLite OperationalError (database is locked):** Concurrent writes from simultaneous AI agents.
4. **Git Hook Environment Drift:** Shell pathing failures between Git for Windows (Bash) and PowerShell.
5. **Deadlock from Stale Agent Sessions:** Abandoned agent sessions leaving orphaned file reservations.

---

## 1. Pre-Push Hook Latency Spike (6.2s Freeze)

### The Incident
In our initial prototype, the Git pre-push hook attempted to perform deep semantic conflict detection on every git push. When a developer executed git push, the hook extracted the full git diff, computed dense ONNX neural embeddings over the modified code chunks, and performed vector similarity comparisons against past commit intents.

On medium-sized repositories (commits touching 5-15 files), git push froze for **6,200ms to 8,500ms**. In developer testing, this latency caused immediate frustration, leading engineers to bypass the hook using git push --no-verify, which completely defeated the purpose of the safety guardrail.

### Diagnosis
Benchmarking the execution pipeline revealed that 98% of the latency was spent:
1. Parsing raw diff ASTs into chunk boundaries.
2. Loading the vector inference model into CPU memory inside a short-lived ephemeral process.
3. Calculating vector dot-products over hundreds of tokens per push.

### The Recovery
We decoupled heavy semantic indexing from the pre-push interceptor:
1. **Asynchronous Intent Registration:** AI agents register their active file touch-sets and stated intent (stated_intent) *when their task starts* via the CLI (memoryctl session-start) or the Model Context Protocol (MCP) server.
2. **Sub-Millisecond Interceptor Query:** The Git pre-push hook now performs a pure mathematical set-intersection:
   \text{Collisions} = \text{set}(\text{pushed\_files}) \cap \text{set}(\text{active\_session\_files})
3. **Instant Latency:** Interceptor execution dropped from **6,200ms down to under 12ms**, guaranteeing zero developer friction while providing richer warnings containing the other agent's human-readable intent.

---

## 2. Context Window Bloat & Model Starvation

### The Incident
When injecting recalled project memories (architectural decision records, past bug fixes, security guidelines) into LLM prompts via memoryctl recall or Cursor MCP tool calls, naive string concatenation of all matching memories quickly bloated prompts by 3,000+ tokens. For smaller, faster reasoning models (e.g., Claude 3.5 Haiku, Gemini Flash), this consumed up to 75% of the effective context window, causing response truncation and elevated API billing costs.

### Diagnosis
Vector search alone returns raw top-$ entries regardless of document length. A single verbose ADR describing a database migration could consume 1,200 tokens, starving subsequent results and squeezing out user instructions.

### The Recovery
We implemented a hard **Token Budget Compressor** (memory/compressor.py):
1. Integrated OpenAI's 	iktoken tokenizer using the cl100k_base BPE encoding.
2. Implemented a greedy knapsack packing algorithm: entries are prioritized by semantic relevance score and packed into an explicit caller-defined budget (e.g., --budget 400).
3. If an entry exceeds remaining budget headroom, the engine dynamically compresses the text to its structured key resolution line or safely omits it, reporting exact tokens used and tokens saved to the developer:
   `
   Tokens Used: 70 / 300 | Tokens Saved: 142
   `

---

## 3. SQLite Concurrency Failure (database is locked)

### The Incident
When running two concurrent AI agents simultaneously (e.g., Claude Code updating core/auth.py while Codex modified gateway/storage.py), both processes attempted to write to ~/.contextos/memory.db at the same instant. Python's sqlite3 driver raised intermittent sqlite3.OperationalError: database is locked exceptions, crashing agent session registrations.

### Diagnosis
By default, SQLite operates in DELETE journal mode, which locks the entire database file during write transactions, preventing concurrent readers and writers from operating simultaneously.

### The Recovery
1. Enabled **Write-Ahead Logging (WAL)** on the database connection:
   `sql
   PRAGMA journal_mode=WAL;
   `
2. Configured a 5,000ms busy timeout handler:
   `sql
   PRAGMA busy_timeout=5000;
   `
3. Wrapped all database connections in a unified _get_connection() factory in memory/store.py with 	imeout=10.0. Under stress testing with 50 parallel agent threads, zero write-collision errors occurred.

---

## 4. Git Hook Environment Drift Across Platforms

### The Incident
The pre-push hook functioned properly on macOS and Linux but failed silently on Windows machines running Git Bash. Git for Windows executes hooks in an MSYS bash environment where path delimiters (/ vs \) and Python executable bindings (python vs python3 vs py) differ from native Windows Command Prompt or PowerShell. The hook either failed to find the python binary or passed backslash-delimited Windows paths that bash stripped.

### Diagnosis
Git hooks on Windows run inside a simulated POSIX shell (sh.exe). If the hook script invokes python -m hooks.interceptor , MSYS shell word-splitting fails on Windows paths containing spaces or backslashes.

### The Recovery
1. Standardized POSIX-compliant path normalization inside cli/memoryctl.py and hooks/interceptor.py using Path(p).as_posix().
2. Enhanced the hook installer (memoryctl install-hook) to generate a resilient wrapper script that tests for memoryctl in PATH first, falling back to python module execution with quoted argument strings:
   `ash
   if command -v memoryctl >/dev/null 2>&1; then
       memoryctl check-conflicts 
       STATUS=True
   fi
   `
3. Added strict exit code propagation (aise typer.Exit(code=1)) so Git properly halts the push whenever collisions are detected.

---

## 5. Deadlock from Stale Agent Sessions

### The Incident
If an AI agent process crashed, was canceled with Ctrl+C, or was abruptly killed, its session remained permanently flagged as in_progress in SQLite. Any future developer attempting to push code touching the same files was perpetually blocked by the pre-push interceptor.

### Diagnosis
The original schema recorded started_at but had no lease expiration mechanism or heartbeat verification to distinguish between genuinely active sessions and abandoned ones.

### The Recovery
1. Introduced a soft lease time-to-live (TTL) model: sessions older than 4 hours without heartbeats are treated as expired during conflict checks.
2. Added memoryctl session-end <session_id> and automatic cleanup commands to purge orphaned file locks.
3. Provided an immediate escape hatch in the Git pre-push warning banner:
   `ash
   [Context OS] Push paused due to concurrent session collision.
   To force push anyway, run: git push --no-verify
   `

---

## Summary of Results

| Failure | Root Cause | Fix | Metric After Fix |
|---|---|---|---|
| **Hook Latency** | Synchronous neural diff embedding | Async intent indexing + (1)$ set intersection | **6,200ms $\to$ < 12ms** |
| **Context Bloat** | Unbounded string concatenation | 	iktoken knapsack token budget compression | **100% adherence to token budget** |
| **DB Lock Errors** | SQLite default journal contention | WAL mode + usy_timeout=5000 | **0 errors under 50 parallel threads** |
| **Windows Hooks** | MSYS shell path & binary mismatch | Normalized POSIX paths + fallback runner | **100% cross-platform parity** |
| **Deadlock Locks** | Orphaned sessions from crashed agents | Session TTL leases + --no-verify safety bypass | **Zero permanent blocking** |
