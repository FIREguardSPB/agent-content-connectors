"""Self-extension: sandbox isolation, read-only dry-run, promote-after-approval (§7)."""
from __future__ import annotations

from pathlib import Path

import pytest

from broker_connectors import runtime
from broker_connectors.registry import load_builtin_tools
from broker_connectors.selfextend import scaffold


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    sb = tmp_path / "sandbox"
    td = tmp_path / "tools"
    td.mkdir()
    monkeypatch.setattr(scaffold, "SANDBOX_DIR", sb)
    monkeypatch.setattr(scaffold, "TOOLS_DIR", td)
    return sb, td


def test_scaffold_writes_to_sandbox_only(sandbox):
    sb, _ = sandbox
    dest = scaffold.scaffold_tool(
        tool_name="threads_list", platform="threads",
        base_url="https://graph.threads.net", path="v1.0/me/threads",
        is_write=False, http_method="GET",
    )
    assert (dest / "tool.py").is_file()
    assert (dest / "manifest.json").is_file()
    code = scaffold.review_diff("threads_list")
    assert "def threads_list(" in code
    assert "sandbox" in code.lower()  # the header warning


def test_sandbox_tool_not_loaded_by_registry(sandbox):
    scaffold.scaffold_tool(
        tool_name="threads_list2", platform="threads",
        base_url="https://graph.threads.net", path="v1.0/me/threads", is_write=False,
    )
    names = {t.name for t in load_builtin_tools()}
    assert "threads_list2" not in names  # never auto-loaded (§7.2)


async def test_dry_run_read_tool(sandbox, fake_client, monkeypatch):
    monkeypatch.setenv("NANGO_CONN_THREADS", "conn_threads")
    scaffold.scaffold_tool(
        tool_name="threads_list3", platform="threads",
        base_url="https://graph.threads.net", path="v1.0/me/threads",
        is_write=False, http_method="GET",
    )
    out = await scaffold.dry_run("threads_list3")
    assert out["status"] == "dry_run_ok"
    assert fake_client.calls[0]["path"] == "v1.0/me/threads"


async def test_dry_run_refuses_write_tool(sandbox, fake_client):
    scaffold.scaffold_tool(
        tool_name="threads_post", platform="threads",
        base_url="https://graph.threads.net", path="v1.0/me/threads_publish",
        is_write=True, http_method="POST",
    )
    out = await scaffold.dry_run("threads_post")
    assert out["status"] == "refused"
    assert fake_client.calls == []  # a write tool never runs in dry-run


def test_promote_requires_approval(sandbox):
    scaffold.scaffold_tool(
        tool_name="threads_list4", platform="threads",
        base_url="https://graph.threads.net", path="v1.0/me/threads", is_write=False,
    )
    refused = scaffold.promote("threads_list4", approved=False)
    assert refused["status"] == "refused"

    ok = scaffold.promote("threads_list4", approved=True)
    assert ok["status"] == "promoted"
    _, td = sandbox
    assert (Path(td) / "threads_list4.py").is_file()


def test_invalid_tool_name_rejected(sandbox):
    with pytest.raises(ValueError):
        scaffold.scaffold_tool(
            tool_name="Bad Name!", platform="x", base_url="http://x", path="p", is_write=False,
        )
