"""MCP surface for the Dzen browser-automation adapter (§3).

The confirmation-guard lives in the adapter's execute(), so these tools just
delegate — no double confirmation.
"""
from __future__ import annotations

from typing import Any

from ..adapters.dzen import DzenAdapter
from .base import tool

_adapter = DzenAdapter()


@tool(
    name="dzen_list_articles",
    description="List your Dzen articles via browser-automation (read-only). No args.",
    platform="dzen",
    write=False,
)
async def dzen_list_articles() -> Any:
    return await _adapter.execute("list_articles", {})


@tool(
    name="dzen_publish_article",
    description="Publish an article to Yandex Dzen via browser-automation "
    "(WRITE — requires confirm=true). Args: title, body, confirm=false.",
    platform="dzen",
    write=True,
)
async def dzen_publish_article(title: str, body: str, confirm: bool = False) -> Any:
    return await _adapter.execute("publish_article", {"title": title, "body": body, "confirm": confirm})
