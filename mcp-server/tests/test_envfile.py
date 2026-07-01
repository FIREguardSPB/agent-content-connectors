"""envfile.set_var/get_var — idempotent .env editing used by the wizard."""
from __future__ import annotations

from broker_connectors import envfile


def test_append_then_update(tmp_path):
    p = tmp_path / ".env"
    p.write_text("NANGO_HOST=http://localhost:3003\nNANGO_CONN_YOUTUBE=\n")

    envfile.set_var("NANGO_CONN_YOUTUBE", "conn_1", path=p)
    assert envfile.get_var("NANGO_CONN_YOUTUBE", path=p) == "conn_1"

    # update in place, don't duplicate
    envfile.set_var("NANGO_CONN_YOUTUBE", "conn_2", path=p)
    body = p.read_text()
    assert body.count("NANGO_CONN_YOUTUBE=") == 1
    assert envfile.get_var("NANGO_CONN_YOUTUBE", path=p) == "conn_2"

    # append a brand-new key
    envfile.set_var("NANGO_CONN_VK", "conn_vk", path=p)
    assert envfile.get_var("NANGO_CONN_VK", path=p) == "conn_vk"
    assert envfile.get_var("NANGO_HOST", path=p) == "http://localhost:3003"


def test_get_missing_returns_none(tmp_path):
    p = tmp_path / ".env"
    assert envfile.get_var("NOPE", path=p) is None
    p.write_text("# comment\nFOO=bar\n")
    assert envfile.get_var("NOPE", path=p) is None
    assert envfile.get_var("FOO", path=p) == "bar"
