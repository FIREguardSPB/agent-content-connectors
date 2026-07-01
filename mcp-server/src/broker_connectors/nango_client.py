"""Thin async wrapper over the self-hosted Nango HTTP API.

Only three capabilities are exposed, on purpose:
  * proxy_request  -> {NANGO_HOST}/proxy/{path}   (the agent's read/write path)
  * create_connect_session -> mints a Connect UI link for a human to click
  * list_connections -> connection *metadata* (never credentials)

There is deliberately NO method that returns an OAuth token / credentials.
The token never leaves Nango; this satisfies MVP criterion §8.2.
"""
from __future__ import annotations

from typing import Any

import httpx

from .config import Settings, settings as default_settings


class NangoError(RuntimeError):
    """Raised when the Nango API returns a non-2xx response."""

    def __init__(self, status: int, body: Any, *, path: str, method: str):
        self.status = status
        self.body = body
        self.path = path
        self.method = method
        super().__init__(f"Nango {method} {path} -> HTTP {status}: {body!r}")


class NangoClient:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None):
        self.settings = settings or default_settings
        self._client = client  # injectable for tests
        self._owns_client = client is None

    async def __aenter__(self) -> "NangoClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.settings.timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.require_secret()}"}

    # ---- Proxy -----------------------------------------------------------
    async def proxy_request(
        self,
        method: str,
        path: str,
        *,
        provider_config_key: str,
        connection_id: str,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: Any | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
        base_url_override: str | None = None,
        retries: int | None = None,
    ) -> Any:
        """Call an external API through the Nango Proxy.

        Nango injects the connection's OAuth credentials server-side. We only
        pass identifiers, never tokens.
        """
        url = f"{self.settings.nango_host.rstrip('/')}/proxy/{path.lstrip('/')}"
        req_headers = {
            **self._auth_headers(),
            "Provider-Config-Key": provider_config_key,
            "Connection-Id": connection_id,
        }
        if base_url_override:
            req_headers["Base-Url-Override"] = base_url_override
        if retries is not None:
            req_headers["Retries"] = str(retries)
        if headers:
            req_headers.update(headers)

        resp = await self._http().request(
            method.upper(), url, params=params, json=json, data=data, content=content, headers=req_headers
        )
        return self._parse(resp, method=method.upper(), path=f"/proxy/{path}")

    async def proxy_get(self, path: str, **kw: Any) -> Any:
        return await self.proxy_request("GET", path, **kw)

    async def proxy_post(self, path: str, **kw: Any) -> Any:
        return await self.proxy_request("POST", path, **kw)

    async def proxy_delete(self, path: str, **kw: Any) -> Any:
        return await self.proxy_request("DELETE", path, **kw)

    # ---- Connect sessions ------------------------------------------------
    async def create_connect_session(
        self,
        *,
        end_user_id: str,
        email: str | None = None,
        display_name: str | None = None,
        allowed_integrations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a short-lived Connect session and return {token, expires_at, connect_link}.

        The connect_link is a ready-to-open hosted Connect UI URL — a human
        clicks it, logs into the platform, and Nango stores the credentials.
        No 'token'/'OAuth' wording is ever shown to that human (criterion §8.1).
        """
        url = f"{self.settings.nango_host.rstrip('/')}/connect/sessions"
        end_user: dict[str, Any] = {"id": end_user_id}
        if email:
            end_user["email"] = email
        if display_name:
            end_user["display_name"] = display_name
        body: dict[str, Any] = {"end_user": end_user}
        if allowed_integrations:
            body["allowed_integrations"] = allowed_integrations

        resp = await self._http().post(url, json=body, headers=self._auth_headers())
        parsed = self._parse(resp, method="POST", path="/connect/sessions")
        data = parsed.get("data", parsed) if isinstance(parsed, dict) else parsed
        # Build a fallback connect_link if the server didn't return one.
        if isinstance(data, dict) and not data.get("connect_link") and data.get("token"):
            base = self.settings.connect_ui_url.rstrip("/")
            data["connect_link"] = f"{base}/?session_token={data['token']}"
        return data

    # ---- Connections (metadata only) -------------------------------------
    async def list_connections(self, *, connection_id: str | None = None) -> Any:
        """List connection metadata (id, provider, created_at, ...). No secrets."""
        url = f"{self.settings.nango_host.rstrip('/')}/connection"
        params = {"connectionId": connection_id} if connection_id else None
        resp = await self._http().get(url, params=params, headers=self._auth_headers())
        return self._parse(resp, method="GET", path="/connection")

    # ---- internals -------------------------------------------------------
    @staticmethod
    def _parse(resp: httpx.Response, *, method: str, path: str) -> Any:
        try:
            payload: Any = resp.json()
        except ValueError:
            payload = resp.text
        if resp.status_code >= 400:
            raise NangoError(resp.status_code, payload, path=path, method=method)
        return payload
