"""Confirmation-guard for write actions (§4, §8.4).

MCP tools can't block for interactive input mid-call, so we use the same
dry-run pattern the rest of this environment uses: a write tool that is called
without `confirm=true` returns a structured preview describing exactly what it
WOULD do. The orchestrator agent shows that to the human, gets a yes, and
re-calls the tool with `confirm=true`. Only then does the real API call happen.

This is intentionally engine-free (no rules DSL) — enough at this scale (§4).
"""
from __future__ import annotations

from typing import Any

CONFIRMATION_STATUS = "confirmation_required"

# Params whose values must never be echoed back in a preview.
_SENSITIVE_HINTS = ("token", "secret", "password", "cookie", "authorization", "api_key", "apikey")


def _redact(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in params.items():
        if any(h in k.lower() for h in _SENSITIVE_HINTS):
            out[k] = "<redacted>"
        elif isinstance(v, str) and len(v) > 300:
            out[k] = v[:300] + f"... (+{len(v) - 300} chars)"
        else:
            out[k] = v
    return out


def confirmation_preview(action: str, target: str, params: dict[str, Any], *, note: str | None = None) -> dict[str, Any]:
    """Build the preview payload returned when a write is not yet confirmed."""
    msg = (
        f"⚠️ Confirmation required before this WRITE action.\n"
        f"Action: {action}\nTarget: {target}\n"
        f"Re-call the same tool with confirm=true to actually perform it."
    )
    if note:
        msg += f"\nNote: {note}"
    return {
        "status": CONFIRMATION_STATUS,
        "action": action,
        "target": target,
        "params": _redact(params),
        "message": msg,
    }


def require_confirmation(
    confirm: bool, *, action: str, target: str, params: dict[str, Any], note: str | None = None
) -> dict[str, Any] | None:
    """Return a preview dict if not confirmed (caller must return it), else None.

    Usage inside a write tool:
        guard = require_confirmation(confirm, action="publish video",
                                     target=f"youtube:{connection_id}", params={...})
        if guard:
            return guard
        # ... proceed with the real proxy call ...
    """
    if confirm:
        return None
    return confirmation_preview(action, target, params, note=note)
