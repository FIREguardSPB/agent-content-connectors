"""Shared test fixtures: a fake Nango client that records proxy calls.

The fake is the enforcement point for criterion §8.2: it asserts the tool layer
only ever hands Nango identifiers (provider_config_key, connection_id) and body
data — never an OAuth token, never an Authorization header.
"""
from __future__ import annotations

from typing import Any

import pytest

from broker_connectors import runtime


class FakeNangoClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.post_responses: list[Any] = []

    def _record(self, method: str, path: str, kw: dict[str, Any]) -> None:
        # §8.2 guard: tools must never leak a token to us.
        headers = kw.get("headers") or {}
        assert "Authorization" not in headers, "tool leaked an Authorization header"
        for k in kw:
            assert "token" not in k.lower(), f"tool passed a token-shaped kwarg: {k}"
        self.calls.append({"method": method, "path": path, **kw})

    async def proxy_get(self, path: str, **kw: Any) -> Any:
        self._record("GET", path, kw)
        return {"ok": True, "items": []}

    async def proxy_post(self, path: str, **kw: Any) -> Any:
        self._record("POST", path, kw)
        if self.post_responses:
            return self.post_responses.pop(0)
        return {"id": "GEN-123"}

    async def proxy_delete(self, path: str, **kw: Any) -> Any:
        self._record("DELETE", path, kw)
        return {"ok": True}

    async def create_connect_session(self, **kw: Any) -> dict[str, Any]:
        self.calls.append({"method": "CONNECT_SESSION", **kw})
        return {"token": "sess_tok", "expires_at": "2099-01-01T00:00:00Z",
                "connect_link": "http://localhost:3009/?session_token=sess_tok"}

    async def list_connections(self, connection_id: str | None = None) -> Any:
        self.calls.append({"method": "LIST_CONN", "connection_id": connection_id})
        return {"connections": []}

    async def aclose(self) -> None:
        pass


@pytest.fixture
def fake_client() -> FakeNangoClient:
    c = FakeNangoClient()
    runtime.set_client(c)
    yield c
    runtime.set_client(None)
