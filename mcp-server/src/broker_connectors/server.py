"""MCP server entry point.

Builds a FastMCP server by registering every built-in, human-reviewed tool from
the registry. Self-generated tools in sandbox/ are NOT loaded here — they only
reach production after a human promotes them (selfextend/), which is the single
security gate described in §7.2.
"""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .registry import load_builtin_tools

log = logging.getLogger("broker_connectors")


def build_server() -> FastMCP:
    mcp = FastMCP("broker-connectors")
    specs = load_builtin_tools()
    for spec in specs:
        # FastMCP infers the JSON schema from each function's typed signature.
        mcp.add_tool(spec.fn, name=spec.name, description=spec.description)
    log.info("registered %d tools: %s", len(specs), ", ".join(sorted(s.name for s in specs)))
    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_server().run()  # stdio transport by default


if __name__ == "__main__":
    main()
