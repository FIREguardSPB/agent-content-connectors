"""Custom platform adapters for non-OAuth / no-API platforms (§3, §6.6).

Adapters are deliberately NOT coupled to Nango — they follow the uniform
`PlatformAdapter.execute(action, params)` contract so the orchestrator treats
them like any other capability.
"""
from .base import AdapterUnavailable, PlatformAdapter

__all__ = ["PlatformAdapter", "AdapterUnavailable"]
