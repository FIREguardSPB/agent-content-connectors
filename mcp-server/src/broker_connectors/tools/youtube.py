"""YouTube tools over the Nango Proxy (provider: Google/YouTube Data API v3).

Reads are free; writes go through the confirmation-guard (§8.4). None of this
code sees the OAuth token — Nango injects it inside the proxy.
"""
from __future__ import annotations

import os
from typing import Any

from ..confirmation import require_confirmation
from ..runtime import get_client
from ._common import build_multipart_related, resolve
from .base import tool

_GOOGLEAPIS = "https://www.googleapis.com"


@tool(
    name="youtube_list_videos",
    description="List the authenticated channel's own videos (read-only). "
    "Args: max_results (int, default 10), connection_id (optional).",
    platform="youtube",
    write=False,
)
async def youtube_list_videos(max_results: int = 10, connection_id: str | None = None) -> Any:
    pck, cid = resolve("youtube", connection_id, None)
    return await get_client().proxy_get(
        "youtube/v3/search",
        provider_config_key=pck,
        connection_id=cid,
        params={"part": "snippet", "forMine": "true", "type": "video", "maxResults": max_results},
        base_url_override=_GOOGLEAPIS,
    )


@tool(
    name="youtube_upload",
    description="Upload a local video file to YouTube (WRITE — requires confirm=true). "
    "Args: file_path, title, description='', privacy_status='private'|'unlisted'|'public', "
    "tags=[], connection_id (optional), confirm=false.",
    platform="youtube",
    write=True,
)
async def youtube_upload(
    file_path: str,
    title: str,
    description: str = "",
    privacy_status: str = "private",
    tags: list[str] | None = None,
    connection_id: str | None = None,
    confirm: bool = False,
) -> Any:
    pck, cid = resolve("youtube", connection_id, None)
    if not os.path.isfile(file_path):
        return {"status": "error", "message": f"file not found: {file_path}"}
    size = os.path.getsize(file_path)

    guard = require_confirmation(
        confirm,
        action="upload video to YouTube",
        target=f"youtube:{cid}",
        params={
            "file_path": file_path,
            "size_bytes": size,
            "title": title,
            "privacy_status": privacy_status,
            "tags": tags or [],
        },
        note=f"Will publish as {privacy_status!r}. ~{size / 1e6:.1f} MB.",
    )
    if guard:
        return guard

    metadata = {
        "snippet": {"title": title, "description": description, "tags": tags or []},
        "status": {"privacyStatus": privacy_status},
    }
    with open(file_path, "rb") as fh:
        media = fh.read()
    body, content_type = build_multipart_related(metadata, media, "video/*")

    # NOTE: multipart upload is fine for modest files. Very large files should
    # use YouTube's resumable protocol (uploadType=resumable) — see README.
    return await get_client().proxy_post(
        "upload/youtube/v3/videos",
        provider_config_key=pck,
        connection_id=cid,
        params={"part": "snippet,status", "uploadType": "multipart"},
        content=body,
        headers={"Content-Type": content_type},
        base_url_override=_GOOGLEAPIS,
    )
