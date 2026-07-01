"""Scaffolding engine for agent self-extension (§7.1 flow).

Hard invariants (§7.2), enforced structurally:
  * This module NEVER registers OAuth apps on third-party platforms. There is no
    code path that calls a developer console — the most it does about missing
    OAuth apps is *report* that a human must create one (preflight -> NEEDS_OAUTH_APP).
  * Generated code is written to sandbox/ only. It is not importable by the prod
    server (registry.load_builtin_tools ignores sandbox).
  * dry_run refuses to execute WRITE tools. Only read-only calls are allowed
    before a human review.
  * promote() refuses without approved=True, and only then copies the file into
    the built-in tools package so the next server start loads it.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import settings
from ..nango_client import NangoClient
from ..tools.base import REGISTRY, ToolSpec

_HERE = Path(__file__).resolve()
_PKG_DIR = _HERE.parents[1]                 # .../src/broker_connectors
_MCP_ROOT = _HERE.parents[3]                # .../mcp-server
_TEMPLATES = _HERE.parent / "templates"

import os as _os

SANDBOX_DIR = Path(_os.environ.get("BROKER_SANDBOX_DIR", str(_MCP_ROOT / "sandbox")))
TOOLS_DIR = _PKG_DIR / "tools"

_env = Environment(loader=FileSystemLoader(str(_TEMPLATES)), autoescape=select_autoescape([]))
# Jinja has no !r conversion; expose Python repr as a filter for code generation.
_env.filters["repr"] = repr
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,50}$")


class Decision(str, Enum):
    NANGO_WRAPPER = "nango_wrapper"      # provider ready in Nango -> scaffold thin wrapper
    NEEDS_OAUTH_APP = "needs_oauth_app"  # 2a: human must create the OAuth app first
    CUSTOM_ADAPTER = "custom_adapter"    # platform absent from Nango -> browser/other adapter
    UNKNOWN = "unknown"                  # couldn't reach Nango to decide


@dataclass
class Preflight:
    platform: str
    decision: Decision
    provider_in_nango: bool | None
    integration_configured: bool | None
    message: str


# --------------------------------------------------------------------------- #
# §7.1 step 1 — gap discovery
# --------------------------------------------------------------------------- #
def list_current_tools() -> list[str]:
    from ..registry import load_builtin_tools

    return sorted(t.name for t in load_builtin_tools())


# --------------------------------------------------------------------------- #
# §7.2 step 2 — decide the path (does Nango already cover this platform?)
# --------------------------------------------------------------------------- #
async def preflight(platform: str, *, client: NangoClient | None = None) -> Preflight:
    own = client is None
    client = client or NangoClient()
    try:
        provider_in_nango = await _provider_exists(platform, client)
        integration_configured = await _integration_configured(platform, client)
    except Exception as exc:  # network/offline
        return Preflight(platform, Decision.UNKNOWN, None, None,
                         f"Could not query Nango to decide: {exc}")
    finally:
        if own:
            await client.aclose()

    if not provider_in_nango:
        return Preflight(
            platform, Decision.CUSTOM_ADAPTER, False, integration_configured,
            f"{platform!r} is not in Nango's provider catalog. Two sub-cases (§2, §3): "
            "if the platform HAS an OAuth2 API (e.g. VK), add it to Nango as a generic "
            "OAuth2 integration (still needs your OAuth app) and scaffold a thin wrapper; "
            "if it has NO API at all (e.g. Dzen), write a custom PlatformAdapter with "
            "browser-automation.",
        )
    if not integration_configured:
        return Preflight(
            platform, Decision.NEEDS_OAUTH_APP, True, False,
            f"Nango has a provider for {platform!r}, but no integration/OAuth app is "
            "configured yet. Creating the developer app + App Review is a human step "
            "(§2a) — the agent stops here and asks you.",
        )
    return Preflight(
        platform, Decision.NANGO_WRAPPER, True, True,
        f"Nango provider and integration for {platform!r} are ready -> scaffold a thin "
        "MCP wrapper (mechanical).",
    )


async def _provider_exists(platform: str, client: NangoClient) -> bool:
    url = f"{settings.nango_host.rstrip('/')}/providers"
    resp = await client._http().get(url, headers=client._auth_headers())
    if resp.status_code >= 400:
        # /providers may be unauth on some builds; treat 401 as "unknown -> assume absent"
        return False
    data = resp.json()
    items = data.get("data", data) if isinstance(data, dict) else data
    names = {(_slug(x) if isinstance(x, str) else _slug(x.get("name", ""))) for x in items} if items else set()
    return _slug(platform) in names


async def _integration_configured(platform: str, client: NangoClient) -> bool:
    url = f"{settings.nango_host.rstrip('/')}/integrations"
    resp = await client._http().get(url, headers=client._auth_headers())
    if resp.status_code >= 400:
        return False
    data = resp.json()
    items = data.get("data", data) if isinstance(data, dict) else data
    keys = set()
    for x in items or []:
        if isinstance(x, dict):
            keys.add(_slug(x.get("provider", "")))
            keys.add(_slug(x.get("unique_key", x.get("providerConfigKey", ""))))
    return _slug(platform) in keys


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# --------------------------------------------------------------------------- #
# §7.1 step 3/4 — generate into sandbox
# --------------------------------------------------------------------------- #
def scaffold_tool(
    *,
    tool_name: str,
    platform: str,
    base_url: str,
    path: str,
    is_write: bool,
    http_method: str = "GET",
    description: str | None = None,
    provider_config_key: str | None = None,
    action_label: str | None = None,
    generated_note: str = "by selfextend.scaffold_tool",
) -> Path:
    if not _NAME_RE.match(tool_name):
        raise ValueError(f"invalid tool_name {tool_name!r} (expected snake_case identifier)")
    description = description or f"{platform} {tool_name} ({'write' if is_write else 'read'})"
    action_label = action_label or f"{platform} {tool_name}"

    dest = SANDBOX_DIR / tool_name
    dest.mkdir(parents=True, exist_ok=True)

    tool_src = _env.get_template("mcp_tool.py.j2").render(
        tool_name=tool_name,
        platform=platform,
        base_url=base_url,
        path=path,
        is_write=is_write,
        http_method_lower=http_method.lower(),
        description=description,
        provider_config_key=provider_config_key,
        action_label=action_label,
        generated_note=generated_note,
    )
    manifest_src = _env.get_template("manifest.json.j2").render(
        tool_name=tool_name,
        platform=platform,
        is_write=is_write,
        is_write_json="true" if is_write else "false",
        provider_config_key=provider_config_key,
        base_url=base_url,
        path=path,
        http_method=http_method.upper(),
        generated_note=generated_note,
    )
    (dest / "tool.py").write_text(tool_src)
    (dest / "manifest.json").write_text(manifest_src)
    return dest


def review_diff(tool_name: str) -> str:
    """Return the generated code for a human to read before promoting (§7.6)."""
    f = SANDBOX_DIR / tool_name / "tool.py"
    if not f.is_file():
        raise FileNotFoundError(f"no sandboxed tool {tool_name!r} at {f}")
    return f.read_text()


def _manifest(tool_name: str) -> dict[str, Any]:
    return json.loads((SANDBOX_DIR / tool_name / "manifest.json").read_text())


# --------------------------------------------------------------------------- #
# §7.1 step 5 — dry-run (READ ONLY)
# --------------------------------------------------------------------------- #
async def dry_run(tool_name: str, params: dict[str, Any] | None = None) -> Any:
    """Import the sandboxed tool in isolation and call it — refuses WRITE tools."""
    manifest = _manifest(tool_name)
    if manifest.get("is_write"):
        return {"status": "refused", "reason": "dry_run only runs read-only tools (§7.5)"}

    file = SANDBOX_DIR / tool_name / "tool.py"
    before = len(REGISTRY)
    spec_obj = importlib.util.spec_from_file_location(f"_sandbox_{tool_name}", file)
    module = importlib.util.module_from_spec(spec_obj)  # type: ignore[arg-type]
    added: list[ToolSpec] = []
    try:
        spec_obj.loader.exec_module(module)  # type: ignore[union-attr]
        added = REGISTRY[before:]
        target = next((t for t in added if t.name == tool_name), None)
        if target is None:
            return {"status": "error", "reason": "tool did not register under its name"}
        result = await target.fn(params=params)
        return {"status": "dry_run_ok", "tool": tool_name, "result": result}
    finally:
        # never leak a sandbox tool into the shared registry
        del REGISTRY[before:]


# --------------------------------------------------------------------------- #
# §7.1 step 6 — promote after human approval
# --------------------------------------------------------------------------- #
def promote(tool_name: str, *, approved: bool = False) -> dict[str, Any]:
    if not approved:
        return {
            "status": "refused",
            "reason": "promotion requires explicit human approval (approved=True). "
            "This is the single gate that stops the agent self-activating new "
            "capabilities from untrusted content (§7.2).",
        }
    src = SANDBOX_DIR / tool_name / "tool.py"
    if not src.is_file():
        raise FileNotFoundError(f"no sandboxed tool {tool_name!r}")
    dest = TOOLS_DIR / f"{tool_name}.py"
    if dest.exists():
        return {"status": "error", "reason": f"a built-in tool file {dest.name} already exists"}
    shutil.copyfile(src, dest)
    return {
        "status": "promoted",
        "tool": tool_name,
        "installed_to": str(dest),
        "note": "Loaded on next MCP server start. Restart broker-mcp to expose it.",
    }
