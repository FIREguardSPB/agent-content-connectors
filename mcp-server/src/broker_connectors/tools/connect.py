"""Account-connection tools: mint a Connect UI link, list connected accounts.

These do not post content, so they are not write-guarded. `connect_account`
returns a link a human clicks — the word 'token' never appears (§8.1).
"""
from __future__ import annotations

from typing import Any

from ..config import PLATFORM_PROVIDER_KEYS
from ..runtime import get_client
from .base import tool


@tool(
    name="connect_account",
    description="Create a one-click 'Login with ...' link for a platform so a person "
    "(you or a friend) can connect their account. Returns a connect_link URL. "
    "Args: platform (youtube|instagram|vk|...), end_user_id, email='', display_name=''.",
    platform="_connect",
    write=False,
)
async def connect_account(
    platform: str,
    end_user_id: str,
    email: str = "",
    display_name: str = "",
) -> Any:
    provider_key = PLATFORM_PROVIDER_KEYS.get(platform, platform)
    session = await get_client().create_connect_session(
        end_user_id=end_user_id,
        email=email or None,
        display_name=display_name or None,
        allowed_integrations=[provider_key],
    )
    return {
        "status": "ok",
        "platform": platform,
        "connect_link": session.get("connect_link"),
        "expires_at": session.get("expires_at"),
        "instructions": "Open connect_link, log in, and approve access. No tokens to copy.",
    }


@tool(
    name="list_connected_accounts",
    description="List connected accounts (metadata only — provider, id, created_at). "
    "Never returns credentials. Args: connection_id (optional filter).",
    platform="_connect",
    write=False,
)
async def list_connected_accounts(connection_id: str | None = None) -> Any:
    return await get_client().list_connections(connection_id=connection_id)
