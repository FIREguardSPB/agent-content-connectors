"""Personal Content Connectors — thin MCP server over self-hosted Nango.

Design invariant (MVP acceptance criterion §8.2): this package NEVER handles a
raw OAuth token. It talks to Nango's Proxy (`/proxy/...`) and Connect Sessions
(`/connect/sessions`) only. There is deliberately no method that fetches
credentials from Nango — the token stays inside Nango.
"""

__version__ = "0.1.0"
