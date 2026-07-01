"""VK tools over the Nango Proxy.

VK's API takes the access token as a query param, but through Nango the token is
injected server-side, so tools only pass the non-secret params (v, message, etc).
"""
from __future__ import annotations

from typing import Any

from ..confirmation import require_confirmation
from ..runtime import get_client
from ._common import resolve
from .base import tool

_VK_API = "https://api.vk.com/method"
_VK_VERSION = "5.199"


@tool(
    name="vk_post",
    description="Post a text message to a VK wall (WRITE — requires confirm=true). "
    "Args: message, owner_id (optional, e.g. -<group_id> for a community), "
    "connection_id (optional), confirm=false.",
    platform="vk",
    write=True,
)
async def vk_post(
    message: str,
    owner_id: str | None = None,
    connection_id: str | None = None,
    confirm: bool = False,
) -> Any:
    pck, cid = resolve("vk", connection_id, None)
    guard = require_confirmation(
        confirm,
        action="post to VK wall",
        target=f"vk:{owner_id or 'self'}:{cid}",
        params={"owner_id": owner_id, "message": message},
    )
    if guard:
        return guard

    params: dict[str, Any] = {"message": message, "v": _VK_VERSION}
    if owner_id:
        params["owner_id"] = owner_id
    return await get_client().proxy_post(
        "wall.post",
        provider_config_key=pck,
        connection_id=cid,
        params=params,
        base_url_override=_VK_API,
    )
