"""Shared helpers for platform tools: connection resolution + multipart media."""
from __future__ import annotations

import uuid
from typing import Any

from ..config import PLATFORM_PROVIDER_KEYS, default_connection_id


class ConnectionUnresolved(RuntimeError):
    pass


def resolve(platform: str, connection_id: str | None, provider_config_key: str | None) -> tuple[str, str]:
    """Return (provider_config_key, connection_id), filling from env defaults.

    Keeping this in one place is what makes 'add a platform = config only' true
    (§8.3): a new platform needs a PLATFORM_PROVIDER_KEYS entry (or env) and a
    connection id, no changes to the proxy/confirmation machinery.
    """
    pck = provider_config_key or PLATFORM_PROVIDER_KEYS.get(platform, platform)
    cid = connection_id or default_connection_id(platform)
    if not cid:
        raise ConnectionUnresolved(
            f"No connection_id for platform {platform!r}. Pass connection_id=... or set "
            f"NANGO_CONN_{platform.upper()} after connecting the account via Connect UI."
        )
    return pck, cid


def build_multipart_related(metadata: dict[str, Any], media: bytes, media_type: str) -> tuple[bytes, str]:
    """Build a multipart/related body (metadata JSON + media) for Google uploads.

    Returns (body_bytes, content_type_header).
    """
    import json

    boundary = f"===============broker-{uuid.uuid4().hex}=="
    crlf = b"\r\n"
    parts = [
        f"--{boundary}".encode(),
        b"Content-Type: application/json; charset=UTF-8",
        b"",
        json.dumps(metadata).encode(),
        f"--{boundary}".encode(),
        f"Content-Type: {media_type}".encode(),
        b"",
        media,
        f"--{boundary}--".encode(),
        b"",
    ]
    body = crlf.join(parts)
    return body, f'multipart/related; boundary="{boundary}"'
