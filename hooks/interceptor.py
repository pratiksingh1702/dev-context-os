"""Pre-Push Conflict Interceptor Daemon.

Reads changed files and evaluates them against the active SQLite session registry.
Outputs formatted, explainable conflict warnings with other agents' stated intents.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich import print
from rich.console import Console
from rich.panel import Panel

from memory.conflict import ConflictDetector
from memory.store import MemoryStore

console = Console()


def intercept_push(touched_files: list[str]) -> int:
    if not touched_files:
        return 0

    store = MemoryStore()
    detector = ConflictDetector(store)

    conflicts = detector.detect_conflicts(touched_files)
    if not conflicts:
        return 0

    console.print()
    console.print(
        Panel.fit(
            "[bold red][!] CONCURRENT EDIT WARNING DETECTED BEFORE PUSH[/bold red]\n"
            "[yellow]One or more files in this push are currently being modified by another active AI session.[/yellow]",
            border_style="red",
        )
    )

    for c in conflicts:
        risk_color = "red" if c.risk_level == "HIGH" else "yellow"
        console.print(f"• File: [bold cyan]{c.file_path}[/bold cyan] ([bold {risk_color}]Risk: {c.risk_level}[/bold {risk_color}])")
        console.print(f"  ├── Active Session: [magenta]{c.agent_name} ({c.developer_name})[/magenta]")
        console.print(f"  ├── Stated Intent: \"[bold white]{c.stated_intent}[/bold white]\"")
        console.print(f"  └── Started At: {c.started_at}")
        console.print()

    console.print("[dim]Suggested Action: Coordinate with the developer/agent or rebase before overwriting.[/dim]\n")
    return 1


if __name__ == "__main__":
    files = sys.argv[1:]
    exit_code = intercept_push(files)
    sys.exit(exit_code)
