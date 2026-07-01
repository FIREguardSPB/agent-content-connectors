"""Nango integration provisioning (create/update/find-connection), mocked httpx."""
from __future__ import annotations

import pytest

from broker_connectors import provisioning
from broker_connectors.config import Settings


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    s = Settings(nango_host="http://nango.test", nango_secret_key="SECRET")
    monkeypatch.setattr(provisioning, "settings", s)


async def test_upsert_creates_when_absent(httpx_mock):
    httpx_mock.add_response(method="GET", url="http://nango.test/integrations/youtube", status_code=404)
    httpx_mock.add_response(method="POST", url="http://nango.test/integrations",
                            json={"data": {"unique_key": "youtube"}}, status_code=200)
    res = await provisioning.upsert_integration("youtube", "CID", "SEC")
    assert res["ok"] and res["action"] == "created" and res["provider"] == "youtube"


async def test_upsert_updates_when_present(httpx_mock):
    httpx_mock.add_response(method="GET", url="http://nango.test/integrations/youtube",
                            json={"data": {"unique_key": "youtube"}}, status_code=200)
    httpx_mock.add_response(method="PATCH", url="http://nango.test/integrations/youtube",
                            json={"data": {}}, status_code=200)
    res = await provisioning.upsert_integration("youtube", "CID", "SEC2")
    assert res["ok"] and res["action"] == "updated"


async def test_upsert_surfaces_api_error(httpx_mock):
    httpx_mock.add_response(method="GET", url="http://nango.test/integrations/youtube", status_code=404)
    httpx_mock.add_response(method="POST", url="http://nango.test/integrations",
                            json={"error": "bad provider"}, status_code=400)
    res = await provisioning.upsert_integration("youtube", "CID", "SEC")
    assert res["ok"] is False and res["status"] == 400


async def test_find_connection_matches_by_provider_key(httpx_mock):
    httpx_mock.add_response(
        method="GET", url="http://nango.test/connection",
        json={"connections": [
            {"connection_id": "conn_a", "provider_config_key": "vk", "created_at": "2026-01-01"},
            {"connection_id": "conn_b", "provider_config_key": "youtube", "created_at": "2026-02-01"},
            {"connection_id": "conn_c", "provider_config_key": "youtube", "created_at": "2026-03-01"},
        ]},
    )
    conn = await provisioning.find_connection("youtube")
    assert conn is not None
    assert conn["connection_id"] == "conn_c"  # newest by created_at


async def test_find_connection_none_when_absent(httpx_mock):
    httpx_mock.add_response(method="GET", url="http://nango.test/connection", json={"connections": []})
    assert await provisioning.find_connection("youtube") is None
