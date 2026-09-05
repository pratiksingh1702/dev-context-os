"""CLI Interface for AI Developer Context OS (`memoryctl`).

Commands:
- `memoryctl remember "<content>"`
- `memoryctl recall "<query>"`
- `memoryctl session start / end`
- `memoryctl status`
- `memoryctl check-conflicts`
- `memoryctl install-hook` (Install Git pre-push hook in current repository)
- `memoryctl mcp` (Run Model Context Protocol stdio server)
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import List, Optional

# Bootstrap project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from memory.compressor import ContextCompressor
from memory.conflict import ConflictDetector
from memory.semantic import SemanticMemorySearch
from memory.store import MemoryStore

app = typer.Typer(help="AI Developer Context OS CLI - Project Memory & Conflict Awareness")
console = Console()
store = MemoryStore()
searcher = SemanticMemorySearch()
compressor = ContextCompressor()
conflict_detector = ConflictDetector(store)


@app.command()
def remember(
    content: str = typer.Argument(..., help="The decision, bug fix, or architecture note to store"),
    title: str = typer.Option("Project Note", "--title", "-t", help="Title for this memory entry"),
    category: str = typer.Option("decision", "--category", "-c", help="Category: adr | bug_fix | architecture | decision"),
    files: Optional[List[str]] = typer.Option(None, "--file", "-f", help="Files associated with this decision"),
    tool: str = typer.Option("user", "--tool", help="Source tool: claude_code | codex | cursor | user"),
):
    """Store a persistent project memory or resolved bug fix."""
    entry_id = store.add_memory(
        title=title,
        category=category,
        content=content,
        affected_files=files or [],
        source_tool=tool,
    )
    console.print(f"[green][+] Memory stored successfully![/green] (ID: [bold cyan]{entry_id}[/bold cyan])")


@app.command()
def recall(
    query: str = typer.Argument(..., help="Search query for project memories"),
    budget: int = typer.Option(1000, "--budget", "-b", help="Max token budget for returned context"),
    limit: int = typer.Option(5, "--limit", "-l", help="Max number of candidate memories to fetch"),
):
    """Retrieve relevant project memory with strict token budget packing."""
    all_mems = store.get_all_memories(limit=50)
    if not all_mems:
        console.print("[yellow]No memory entries found in project database.[/yellow]")
        return

    ranked = searcher.search(query, all_mems, top_k=limit)
    packed, tokens_used, tokens_saved = compressor.pack_memories(ranked, token_budget=budget)

    console.print(Panel(f"[bold cyan][*] Project Context Recall for:[/bold cyan] '{query}'", style="cyan"))
    for m in packed:
        cat_color = "green" if m["category"] == "bug_fix" else "blue"
        console.print(f"• [{cat_color}][{m['category'].upper()}][/{cat_color}] [bold]{m['title']}[/bold]")
        console.print(f"  {m['content']}")
        if m["affected_files"]:
            console.print(f"  [dim]Files: {', '.join(m['affected_files'])}[/dim]")
        console.print()

    console.print(f"[dim]Tokens Used: {tokens_used} / {budget} | Tokens Saved: {tokens_saved}[/dim]")


@app.command("session-start")
def session_start(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name e.g. claude_code, codex, cursor"),
    developer: str = typer.Option("Dev", "--dev", "-d", help="Developer name"),
    intent: str = typer.Option(..., "--intent", "-i", help="Why this change is being made"),
    files: List[str] = typer.Option(..., "--file", "-f", help="Files being touched by this session"),
    task: str = typer.Option("Feature Work", "--task", "-t", help="High-level task summary"),
):
    """Register an active AI coding session to prevent merge conflicts."""
    session_id = store.start_session(
        agent_name=agent,
        developer_name=developer,
        task_description=task,
        stated_intent=intent,
        files_accessed=files,
    )
    console.print(f"[green][+] Session registered:[/green] [bold cyan]{session_id}[/bold cyan]")
    console.print(f"  [dim]Locked Files: {', '.join(files)}[/dim]")


@app.command("session-end")
def session_end(
    session_id: str = typer.Argument(..., help="Session ID to terminate"),
):
    """Mark an AI session as completed and release its file locks."""
    store.end_session(session_id, status="completed")
    console.print(f"[green][+] Session {session_id} ended. File locks released.[/green]")


@app.command("status")
def status():
    """Display active AI agent sessions and file touch-sets."""
    active = store.get_active_sessions()
    all_mems = store.get_all_memories()

    table = Table(title="[*] AI Developer Context OS - Active Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Agent / Dev", style="magenta")
    table.add_column("Stated Intent", style="white")
    table.add_column("Locked Files", style="yellow")

    for s in active:
        table.add_row(
            s["session_id"],
            f"{s['agent_name']} ({s['developer_name']})",
            s["stated_intent"],
            ", ".join(s["files_accessed"]),
        )

    console.print(table)
    console.print(f"[dim]Total Persistent Memories Stored: {len(all_mems)}[/dim]")


@app.command("check-conflicts")
def check_conflicts(
    files: Optional[List[str]] = typer.Argument(None, help="Files to check (positional arguments from git)"),
    file_opts: Optional[List[str]] = typer.Option(None, "--file", "-f", help="Files to check via flag"),
):
    """Check if specified files are concurrently modified by active sessions."""
    targets: List[str] = []
    if files:
        targets.extend(files)
    if file_opts:
        targets.extend(file_opts)
    
    # Clean whitespace and empty entries
    targets = [f.strip() for f in targets if f and f.strip()]
    if not targets:
        console.print("[dim]No files provided to check.[/dim]")
        return

    conflicts = conflict_detector.detect_conflicts(targets)
    if not conflicts:
        console.print("[green][+] No conflicts detected on specified files.[/green]")
        return

    console.print()
    console.print(
        Panel.fit(
            "[bold red][!] CONCURRENT EDIT WARNING DETECTED BEFORE PUSH[/bold red]\n"
            "[yellow]One or more files in this push are currently being modified by another active AI session.[/yellow]",
            border_style="red",
        )
    )
    for c in conflicts:
        risk_style = "bold red" if c.risk_level == "HIGH" else "bold yellow"
        console.print(f"• File: [bold cyan]{c.file_path}[/bold cyan] ([{risk_style}]Risk: {c.risk_level}[/{risk_style}])")
        console.print(f"  ├── Active Agent: [magenta]{c.agent_name} ({c.developer_name})[/magenta]")
        console.print(f"  ├── Stated Intent: \"[bold white]{c.stated_intent}[/bold white]\"")
        console.print(f"  └── Started At: {c.started_at}")
        console.print()

    console.print("[dim]Suggested Action: Review the active session's intent or rebase before overwriting.[/dim]\n")
    # Return exit code 1 to halt git push
    raise typer.Exit(code=1)


@app.command("install-hook")
def install_hook(
    repo_path: Path = typer.Option(Path("."), "--repo", "-r", help="Path to target Git repository"),
):
    """Install the Context OS pre-push conflict interceptor in any Git repository."""
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        console.print(f"[red]Error: {repo_path} is not a valid Git repository (.git not found).[/red]")
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    pre_push_path = hooks_dir / "pre-push"

    hook_script = """#!/bin/sh
# Context OS Pre-Push Interceptor Hook
CHANGED=$(git diff --name-only origin/main 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null)
if [ -n "$CHANGED" ]; then
    if command -v memoryctl >/dev/null 2>&1; then
        memoryctl check-conflicts $CHANGED
        STATUS=$?
    else
        python -m cli.memoryctl check-conflicts $CHANGED 2>/dev/null || python -m hooks.interceptor $CHANGED
        STATUS=$?
    fi
    if [ $STATUS -ne 0 ]; then
        echo ""
        echo "[Context OS] Push paused due to concurrent session collision."
        echo "To force push anyway, run: git push --no-verify"
        exit 1
    fi
fi
exit 0
"""
    with open(pre_push_path, "w", encoding="utf-8") as f:
        f.write(hook_script)

    # Set executable permissions
    try:
        pre_push_path.chmod(pre_push_path.stat().st_mode | stat.S_IEXEC)
    except Exception:
        pass

    console.print(f"[green][+] Installed Git pre-push hook in:[/green] {pre_push_path}")


@app.command("mcp")
def run_mcp():
    """Launch the Model Context Protocol stdio server."""
    from mcp.server import main
    main()


if __name__ == "__main__":
    app()
