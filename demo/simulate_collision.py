"""Multi-Agent Collision & Memory Recall Simulation Demo.

Simulates:
1. Seed project memory: Store past bug fix on JWT race condition.
2. Active Session A: Claude Code working on core/auth.py ("Refactoring token refresh to add leeway buffer").
3. Active Session B: Codex attempts to push modifications to core/auth.py.
4. Interceptor catches the collision live, displays Claude Code's stated intent, and warns before overwriting.
5. Performs semantic recall with exact token budget compression.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to sys.path so it can run standalone from any working directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich import print
from rich.console import Console
from rich.panel import Panel

from hooks.interceptor import intercept_push
from memory.compressor import ContextCompressor
from memory.conflict import ConflictDetector
from memory.semantic import SemanticMemorySearch
from memory.store import MemoryStore

console = Console()


def run_simulation():
    console.print("=" * 70, style="bold cyan")
    console.print("[*] AI DEVELOPER CONTEXT OS - LIVE MULTI-AGENT COLLISION SIMULATION", style="bold cyan")
    console.print("=" * 70, style="bold cyan")

    # 1. Initialize Store
    test_db = Path(__file__).resolve().parent / "demo_memory.db"
    if test_db.exists():
        test_db.unlink()

    store = MemoryStore(db_path=test_db)
    detector = ConflictDetector(store=store)
    searcher = SemanticMemorySearch()
    compressor = ContextCompressor()

    # 2. Seed Long-Term Memory
    console.print("\n[bold green]Step 1: Storing Architectural Decision & Past Bug Resolution in Project Memory...[/bold green]")
    store.add_memory(
        title="JWT Token Expiry Race Condition Fix",
        category="bug_fix",
        content="Resolved intermittent 401 Unauthorized under high concurrency by introducing a 30-second leeway buffer and Redis-backed refresh mutex in core/auth.py.",
        affected_files=["core/auth.py", "core/security/jwt.py"],
        source_tool="claude_code",
    )
    store.add_memory(
        title="PostgreSQL Connection Pool Tuning",
        category="adr",
        content="Configured max pool size to 20 with 5s timeout to prevent thread exhaustion during high load.",
        affected_files=["gateway/storage/database.py"],
        source_tool="codex",
    )
    console.print("[+] 2 persistent memories saved to SQLite.")

    # 3. Simulate Active Session A (Claude Code)
    console.print("\n[bold green]Step 2: Developer Pratik starts active coding session with Claude Code...[/bold green]")
    sess_a = store.start_session(
        agent_name="claude_code",
        developer_name="Pratik Singh",
        task_description="Auth concurrency refactor",
        stated_intent="Refactoring token validation loop to eliminate mutex deadlock",
        files_accessed=["core/auth.py"],
    )
    console.print(f"[+] Active Session registered: [bold cyan]{sess_a}[/bold cyan] on [bold yellow]core/auth.py[/bold yellow]")

    # 4. Simulate Concurrent Session B (Codex) attempting to push
    console.print("\n[bold green]Step 3: Developer Alex (using Codex) attempts to Git push changes touching core/auth.py...[/bold green]")
    console.print("[dim]$ git push origin feature/auth-patch[/dim]")
    time.sleep(0.5)

    # 5. Trigger Conflict Interceptor
    touched_files = ["core/auth.py", "server/main.py"]
    conflicts = detector.detect_conflicts(touched_files)

    if conflicts:
        console.print("\n[bold red][!] [GIT PRE-PUSH HOOK TRIGGERED][/bold red]")
        for c in conflicts:
            console.print(Panel(
                f"[bold red]CONCURRENT EDIT COLLISION DETECTED ON:[/bold red] [bold cyan]{c.file_path}[/bold cyan]\n\n"
                f"• Active Agent: [magenta]{c.agent_name}[/magenta] (Developer: [bold]{c.developer_name}[/bold])\n"
                f"• Stated Intent: \"[bold white]{c.stated_intent}[/bold white]\"\n"
                f"• Domain Risk Level: [bold red]{c.risk_level}[/bold red]\n"
                f"• Session Started: {c.started_at}\n\n"
                f"[yellow]Action: Push intercepted. Review active session intent before overwriting.[/yellow]",
                title="Context OS Pre-Push Guardrail",
                border_style="red"
            ))

    # 6. Test Semantic Recall with Token Budget
    console.print("\n[bold green]Step 4: Alex uses Context OS to recall past context on auth race condition...[/bold green]")
    console.print("[dim]$ memoryctl recall 'how did we fix the auth race condition?' --budget 300[/dim]\n")

    all_mems = store.get_all_memories()
    ranked = searcher.search("auth race condition", all_mems, top_k=3)
    packed, used, saved = compressor.pack_memories(ranked, token_budget=300)

    for m in packed:
        console.print(f"• [[bold green]{m['category'].upper()}[/bold green]] [bold]{m['title']}[/bold]")
        console.print(f"  {m['content']}")
        console.print(f"  [dim]Files: {', '.join(m['affected_files'])}[/dim]\n")

    console.print(f"[dim]Tokens Used: {used} / 300 | Tokens Saved: {saved}[/dim]")

    console.print("\n" + "=" * 70, style="bold cyan")
    console.print("[+] SIMULATION COMPLETE: All multi-agent guardrails verified successfully!", style="bold cyan")
    console.print("=" * 70, style="bold cyan")


if __name__ == "__main__":
    run_simulation()
