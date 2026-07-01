"""Tool declaration primitives.

A tool is a plain async function tagged with @tool(...). Registration into the
actual MCP server happens later in server.py by iterating REGISTRY, so the same
metadata (platform, write) can drive confirmation policy and discovery (§8.3).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

ToolFn = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    fn: ToolFn
    description: str
    platform: str
    write: bool


# Populated at import time by the @tool decorator on every tool module.
REGISTRY: list[ToolSpec] = []


def tool(*, name: str, description: str, platform: str, write: bool = False) -> Callable[[ToolFn], ToolFn]:
    def deco(fn: ToolFn) -> ToolFn:
        if any(t.name == name for t in REGISTRY):
            raise ValueError(f"duplicate tool name registered: {name!r}")
        REGISTRY.append(ToolSpec(name=name, fn=fn, description=description, platform=platform, write=write))
        return fn

    return deco


def clear_registry() -> None:
    """Test helper — reset registered tools."""
    REGISTRY.clear()
