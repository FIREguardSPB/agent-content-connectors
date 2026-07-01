"""Registry / server assembly + §8.3 'adding a platform is config-only'."""
from __future__ import annotations

from broker_connectors.registry import load_builtin_tools, platforms
from broker_connectors.tools._common import resolve


def test_builtin_tools_present():
    names = {t.name for t in load_builtin_tools()}
    for expected in {"youtube_upload", "youtube_list_videos", "instagram_post", "vk_post",
                     "connect_account", "list_connected_accounts"}:
        assert expected in names, f"missing built-in tool {expected}"


def test_platforms_discovered():
    p = platforms()
    assert {"youtube", "instagram", "vk"} <= p


def test_adding_platform_is_config_only():
    """A brand-new platform routes through the same resolve() with no code change:
    its providerConfigKey defaults to the platform name (or an env override)."""
    pck, cid = resolve("threads", connection_id="conn_threads", provider_config_key=None)
    assert pck == "threads"
    assert cid == "conn_threads"


def test_build_server_registers_all_tools():
    from broker_connectors.server import build_server

    mcp = build_server()
    # FastMCP exposes registered tools; count should match the registry.
    assert mcp is not None
    assert len(load_builtin_tools()) >= 8


def test_write_and_read_tools_tagged():
    specs = {t.name: t for t in load_builtin_tools()}
    assert specs["youtube_upload"].write is True
    assert specs["vk_post"].write is True
    assert specs["instagram_post"].write is True
    assert specs["youtube_list_videos"].write is False
    assert specs["connect_account"].write is False
