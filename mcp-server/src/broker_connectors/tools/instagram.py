"""Instagram tools over the Nango Proxy (Instagram Graph API / Meta).

Posting an image is the standard two-step Graph flow: create a media container,
then publish it. The Page/IG access token is injected by Nango.
"""
from __future__ import annotations

import os
from typing import Any

from ..confirmation import require_confirmation
from ..runtime import get_client
from ._common import resolve
from .base import tool

_GRAPH = "https://graph.facebook.com"
_GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v21.0")


@tool(
    name="instagram_list_media",
    description="List recent media for an Instagram Business account (read-only). "
    "Args: ig_user_id, max_results=10, connection_id (optional).",
    platform="instagram",
    write=False,
)
async def instagram_list_media(ig_user_id: str, max_results: int = 10, connection_id: str | None = None) -> Any:
    pck, cid = resolve("instagram", connection_id, None)
    return await get_client().proxy_get(
        f"{_GRAPH_VERSION}/{ig_user_id}/media",
        provider_config_key=pck,
        connection_id=cid,
        params={"fields": "id,caption,media_type,permalink,timestamp", "limit": max_results},
        base_url_override=_GRAPH,
    )


@tool(
    name="instagram_post",
    description="Publish an image post to Instagram (WRITE — requires confirm=true). "
    "Two-step Graph flow (create container -> publish). "
    "Args: ig_user_id, image_url (publicly reachable), caption='', "
    "connection_id (optional), confirm=false.",
    platform="instagram",
    write=True,
)
async def instagram_post(
    ig_user_id: str,
    image_url: str,
    caption: str = "",
    connection_id: str | None = None,
    confirm: bool = False,
) -> Any:
    pck, cid = resolve("instagram", connection_id, None)
    guard = require_confirmation(
        confirm,
        action="publish image post to Instagram",
        target=f"instagram:{ig_user_id}:{cid}",
        params={"ig_user_id": ig_user_id, "image_url": image_url, "caption": caption},
    )
    if guard:
        return guard

    client = get_client()
    container = await client.proxy_post(
        f"{_GRAPH_VERSION}/{ig_user_id}/media",
        provider_config_key=pck,
        connection_id=cid,
        params={"image_url": image_url, "caption": caption},
        base_url_override=_GRAPH,
    )
    creation_id = container.get("id") if isinstance(container, dict) else None
    if not creation_id:
        return {"status": "error", "step": "create_container", "response": container}

    published = await client.proxy_post(
        f"{_GRAPH_VERSION}/{ig_user_id}/media_publish",
        provider_config_key=pck,
        connection_id=cid,
        params={"creation_id": creation_id},
        base_url_override=_GRAPH,
    )
    return {"status": "published", "creation_id": creation_id, "result": published}
