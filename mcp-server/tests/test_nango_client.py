"""NangoClient contract + the structural no-token invariant (§8.2)."""
from __future__ import annotations

import httpx
import pytest

from broker_connectors.config import Settings
from broker_connectors.nango_client import NangoClient, NangoError


def _client(handler) -> NangoClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    settings = Settings(nango_host="http://nango.test", nango_secret_key="SECRET_KEY_XYZ")
    return NangoClient(settings=settings, client=http)


async def test_proxy_sends_correct_headers_and_path():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        return httpx.Response(200, json={"ok": True})

    c = _client(handler)
    await c.proxy_get("youtube/v3/search", provider_config_key="youtube",
                      connection_id="conn1", params={"part": "snippet"})

    assert seen["url"] == "http://nango.test/proxy/youtube/v3/search?part=snippet"
    assert seen["headers"]["authorization"] == "Bearer SECRET_KEY_XYZ"
    assert seen["headers"]["provider-config-key"] == "youtube"
    assert seen["headers"]["connection-id"] == "conn1"


async def test_proxy_forwards_base_url_override_and_retries():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        return httpx.Response(200, json={})

    c = _client(handler)
    await c.proxy_post("wall.post", provider_config_key="vk", connection_id="c",
                       base_url_override="https://api.vk.com/method", retries=3)
    assert seen["headers"]["base-url-override"] == "https://api.vk.com/method"
    assert seen["headers"]["retries"] == "3"


async def test_proxy_raises_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "forbidden"})

    c = _client(handler)
    with pytest.raises(NangoError) as ei:
        await c.proxy_get("x", provider_config_key="p", connection_id="c")
    assert ei.value.status == 403


async def test_connect_session_builds_link_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"token": "T", "expires_at": "later"}})

    c = _client(handler)
    data = await c.create_connect_session(end_user_id="me", allowed_integrations=["youtube"])
    assert data["token"] == "T"
    assert data["connect_link"].endswith("session_token=T")


def test_client_has_no_credentials_fetch_method():
    """§8.2: there must be no way to pull a raw token out of Nango via this client."""
    banned = {"get_credentials", "get_token", "get_connection_credentials", "credentials", "token"}
    public = {n for n in dir(NangoClient) if not n.startswith("_")}
    assert not (public & banned), f"NangoClient exposes credential access: {public & banned}"


def test_require_secret_raises_when_missing():
    s = Settings(nango_host="http://x", nango_secret_key=None)
    with pytest.raises(RuntimeError):
        s.require_secret()
