"""Confirmation-guard behaviour (§8.4)."""
from __future__ import annotations

from broker_connectors.confirmation import (
    CONFIRMATION_STATUS,
    confirmation_preview,
    require_confirmation,
)


def test_unconfirmed_returns_preview():
    guard = require_confirmation(False, action="post", target="vk:self", params={"message": "hi"})
    assert guard is not None
    assert guard["status"] == CONFIRMATION_STATUS
    assert guard["action"] == "post"
    assert "confirm=true" in guard["message"]


def test_confirmed_returns_none():
    assert require_confirmation(True, action="post", target="x", params={}) is None


def test_preview_redacts_sensitive_and_truncates():
    p = confirmation_preview(
        "upload", "yt:1",
        {"title": "t", "api_key": "supersecret", "blob": "x" * 500},
    )
    assert p["params"]["api_key"] == "<redacted>"
    assert p["params"]["blob"].endswith("chars)")
    assert p["params"]["title"] == "t"
