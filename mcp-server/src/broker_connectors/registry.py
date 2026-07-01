"""Tool discovery.

Built-in, human-reviewed tools live in `broker_connectors.tools.*` and are the
only things loaded into the production MCP server. Self-generated tools live in
`sandbox/` and are NEVER imported here — they only enter production after a
human promotes them (see selfextend/). This module is the single gate that keeps
that invariant (§7.2).
"""
from __future__ import annotations

import importlib
import pkgutil

from . import tools as tools_pkg
from .tools.base import REGISTRY, ToolSpec

# Modules under broker_connectors.tools that are safe to auto-load.
_SKIP = {"base"}


def load_builtin_tools() -> list[ToolSpec]:
    """Import every built-in tool module so their @tool decorators register."""
    for mod in pkgutil.iter_modules(tools_pkg.__path__):
        if mod.name in _SKIP or mod.name.startswith("_"):
            continue
        importlib.import_module(f"{tools_pkg.__name__}.{mod.name}")
    return list(REGISTRY)


def all_tools() -> list[ToolSpec]:
    return list(REGISTRY)


def platforms() -> set[str]:
    return {t.platform for t in REGISTRY}
