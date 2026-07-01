"""Self-extension: the agent writes a missing tool by template, into sandbox,
for human review before it can ever run a write action (§7)."""
from .scaffold import (
    SANDBOX_DIR,
    Preflight,
    dry_run,
    list_current_tools,
    preflight,
    promote,
    review_diff,
    scaffold_tool,
)

__all__ = [
    "SANDBOX_DIR",
    "Preflight",
    "preflight",
    "scaffold_tool",
    "dry_run",
    "review_diff",
    "promote",
    "list_current_tools",
]
