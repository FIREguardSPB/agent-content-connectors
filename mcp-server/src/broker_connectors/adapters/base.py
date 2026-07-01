"""PlatformAdapter contract (§7.3): uniform execute(action, params).

Write actions reuse the same confirmation-guard as the Nango tools, so the human
gets the same 'confirm before it happens' behaviour regardless of whether the
platform speaks OAuth+Proxy or browser-automation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..confirmation import require_confirmation


class AdapterUnavailable(RuntimeError):
    """Raised when an adapter's runtime dependency (e.g. a browser stack) is missing."""


class PlatformAdapter(ABC):
    #: platform identifier, e.g. "dzen"
    platform: str = ""
    #: action name -> is it a write (needs confirmation)?
    write_actions: set[str] = set()

    @abstractmethod
    async def _do(self, action: str, params: dict[str, Any]) -> Any:
        """Perform the action for real. Called only after confirmation for writes."""

    @abstractmethod
    def actions(self) -> list[str]:
        """List supported action names."""

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> Any:
        params = dict(params or {})
        if action not in self.actions():
            return {"status": "error", "message": f"{self.platform}: unknown action {action!r}",
                    "supported": self.actions()}
        if action in self.write_actions:
            confirm = bool(params.pop("confirm", False))
            guard = require_confirmation(
                confirm,
                action=f"{self.platform}.{action}",
                target=self.platform,
                params=params,
            )
            if guard:
                return guard
        return await self._do(action, params)
