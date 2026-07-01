"""Nango *setup* calls (admin path), separate from the agent's content path.

These configure the developer OAuth app credentials (client_id/secret) inside
Nango and read back connections. client_id/secret are APP config, not user
access tokens — the §8.2 invariant (agent never sees a user OAuth token) is
untouched; this module is used only by the human-facing wizard/CLI, never
exposed as an MCP tool to the orchestrator.
"""
from __future__ import annotations

from typing import Any

import httpx

from .config import settings
from .platforms import PLATFORMS


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.require_secret()}", "Content-Type": "application/json"}


def _base() -> str:
    return settings.nango_host.rstrip("/")


async def integration_exists(unique_key: str, *, client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{_base()}/integrations/{unique_key}", headers=_headers())
    return r.status_code == 200


async def upsert_integration(
    platform_key: str,
    client_id: str,
    client_secret: str,
    *,
    scopes: list[str] | None = None,
    provider: str | None = None,
    unique_key: str | None = None,
) -> dict[str, Any]:
    """Create (or update) a Nango integration with OAuth app credentials.

    Returns {"ok": True, "unique_key": ...} or {"ok": False, "error": ...}.
    """
    meta = PLATFORMS.get(platform_key)
    provider = provider or (meta.provider if meta else platform_key)
    unique_key = unique_key or platform_key
    scope_list = scopes if scopes is not None else (meta.scopes if meta else [])
    if not provider:
        return {"ok": False, "error": f"no Nango provider known for {platform_key!r}"}

    credentials = {
        "type": "OAUTH2",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": ",".join(scope_list),
    }
    async with httpx.AsyncClient(timeout=settings.timeout) as client:
        exists = await integration_exists(unique_key, client=client)
        if exists:
            r = await client.patch(
                f"{_base()}/integrations/{unique_key}",
                headers=_headers(),
                json={"credentials": credentials},
            )
            action = "updated"
        else:
            r = await client.post(
                f"{_base()}/integrations",
                headers=_headers(),
                json={"unique_key": unique_key, "provider": provider, "credentials": credentials},
            )
            action = "created"
        if r.status_code >= 400:
            try:
                body = r.json()
            except ValueError:
                body = r.text
            return {"ok": False, "status": r.status_code, "error": body, "unique_key": unique_key}
        return {"ok": True, "action": action, "unique_key": unique_key, "provider": provider}


async def find_connection(unique_key: str) -> dict[str, Any] | None:
    """Return the newest connection for an integration, or None if not connected yet."""
    async with httpx.AsyncClient(timeout=settings.timeout) as client:
        r = await client.get(f"{_base()}/connection", headers=_headers())
        if r.status_code >= 400:
            return None
        data = r.json()
        conns = data.get("connections", data.get("data", [])) if isinstance(data, dict) else data
        matches = [
            c for c in (conns or [])
            if (c.get("provider_config_key") or c.get("provider") or c.get("integration_id")) == unique_key
        ]
        if not matches:
            return None

        def _cid(c: dict[str, Any]) -> str | None:
            return c.get("connection_id") or c.get("id")

        matches.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        top = matches[0]
        return {"connection_id": _cid(top), "provider_config_key": unique_key, "raw": top}


async def delete_integration(unique_key: str) -> bool:
    async with httpx.AsyncClient(timeout=settings.timeout) as client:
        r = await client.delete(f"{_base()}/integrations/{unique_key}", headers=_headers())
        return r.status_code < 400
