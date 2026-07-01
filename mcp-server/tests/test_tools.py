"""Platform tools: confirmation gating + proxy routing + no-token invariant (§8)."""
from __future__ import annotations

import pytest

from broker_connectors.confirmation import CONFIRMATION_STATUS
from broker_connectors.tools.instagram import instagram_post
from broker_connectors.tools.vk import vk_post
from broker_connectors.tools.youtube import youtube_list_videos, youtube_upload


# ---- §8.4: writes require confirmation, and DON'T touch the API until confirmed ----
async def test_vk_post_requires_confirmation_first(fake_client):
    guard = await vk_post(message="hello", connection_id="c1")
    assert guard["status"] == CONFIRMATION_STATUS
    assert fake_client.calls == []  # nothing hit the proxy


async def test_vk_post_executes_after_confirm(fake_client):
    res = await vk_post(message="hello", owner_id="-42", connection_id="c1", confirm=True)
    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["method"] == "POST" and call["path"] == "wall.post"
    assert call["provider_config_key"] == "vk"
    assert call["connection_id"] == "c1"
    assert call["params"]["message"] == "hello"
    assert call["params"]["owner_id"] == "-42"


async def test_youtube_read_is_free(fake_client):
    await youtube_list_videos(max_results=5, connection_id="yt1")
    assert fake_client.calls[0]["method"] == "GET"
    assert fake_client.calls[0]["path"] == "youtube/v3/search"
    assert fake_client.calls[0]["params"]["forMine"] == "true"


async def test_youtube_upload_confirmation_then_upload(tmp_path, fake_client):
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"\x00\x01\x02fakevideo")

    guard = await youtube_upload(file_path=str(vid), title="T", connection_id="yt1")
    assert guard["status"] == CONFIRMATION_STATUS
    assert fake_client.calls == []

    res = await youtube_upload(file_path=str(vid), title="T", privacy_status="unlisted",
                               connection_id="yt1", confirm=True)
    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["path"] == "upload/youtube/v3/videos"
    assert call["params"]["uploadType"] == "multipart"
    assert call["headers"]["Content-Type"].startswith("multipart/related")


async def test_youtube_upload_missing_file(fake_client):
    res = await youtube_upload(file_path="/no/such.mp4", title="T", connection_id="yt1", confirm=True)
    assert res["status"] == "error"
    assert fake_client.calls == []


async def test_instagram_post_two_step(fake_client):
    fake_client.post_responses = [{"id": "CONTAINER1"}, {"id": "MEDIA1"}]
    res = await instagram_post(ig_user_id="17841400000000000", image_url="https://x/y.jpg",
                               caption="hi", connection_id="ig1", confirm=True)
    assert res["status"] == "published"
    assert res["creation_id"] == "CONTAINER1"
    assert [c["path"] for c in fake_client.calls] == [
        "v21.0/17841400000000000/media",
        "v21.0/17841400000000000/media_publish",
    ]


async def test_no_tool_leaks_a_token(fake_client):
    """The conftest fake asserts per-call; this exercises several tools at once."""
    await youtube_list_videos(connection_id="yt1")
    await vk_post(message="x", connection_id="c1", confirm=True)
    # if any call had smuggled a token, FakeNangoClient._record would have raised
    assert len(fake_client.calls) == 2
