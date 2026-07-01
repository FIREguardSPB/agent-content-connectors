"""Runtime configuration, read from the environment.

Nothing here is secret to the agent except NANGO_SECRET_KEY, which is the
Nango environment secret used to authenticate to the self-hosted Nango API.
It authorises use of the Proxy; it is NOT a platform OAuth token.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _load_dotenv() -> None:
    """Load mcp-server/.env (or $BROKER_ENV_FILE) into os.environ without clobbering
    already-set vars. Zero-dependency, so `broker-mcp`/`broker-connect` work without
    the caller manually sourcing .env."""
    import pathlib

    candidates = []
    override = os.environ.get("BROKER_ENV_FILE")
    if override:
        candidates.append(pathlib.Path(override))
    candidates.append(pathlib.Path(__file__).resolve().parents[2] / ".env")  # mcp-server/.env
    for p in candidates:
        try:
            if not p.is_file():
                continue
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k and k not in os.environ:
                    os.environ[k] = v
            break
        except OSError:
            continue


_load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name, default)
    return val.strip() if isinstance(val, str) else val


@dataclass(frozen=True)
class Settings:
    # Self-hosted Nango API base (the server, not the Connect UI).
    nango_host: str = field(default_factory=lambda: _env("NANGO_HOST", "http://localhost:3003"))
    # Nango environment secret key. Required for Proxy + Connect Sessions.
    nango_secret_key: str | None = field(default_factory=lambda: _env("NANGO_SECRET_KEY"))
    # Public Connect UI base, used only to build human-facing connect links.
    connect_ui_url: str = field(default_factory=lambda: _env("NANGO_CONNECT_UI_URL", "http://localhost:3009"))
    # Default request timeout (seconds) for proxy calls.
    timeout: float = field(default_factory=lambda: float(_env("BROKER_HTTP_TIMEOUT", "30") or 30))

    def require_secret(self) -> str:
        if not self.nango_secret_key:
            raise RuntimeError(
                "NANGO_SECRET_KEY is not set. Get it from the Nango dashboard "
                "(Environment Settings) of your self-hosted instance, or via "
                "`docker exec nango-db psql ...` — see nango/README.md."
            )
        return self.nango_secret_key


# Platform -> default Nango providerConfigKey (the integration id you create in
# Nango). Overridable via env so adding a platform never touches code (§8.3).
PLATFORM_PROVIDER_KEYS: dict[str, str] = {
    "youtube": _env("NANGO_PROVIDER_YOUTUBE", "youtube") or "youtube",
    "instagram": _env("NANGO_PROVIDER_INSTAGRAM", "instagram") or "instagram",
    "vk": _env("NANGO_PROVIDER_VK", "vk") or "vk",
}


def default_connection_id(platform: str) -> str | None:
    """Default connectionId for a platform, e.g. NANGO_CONN_YOUTUBE.

    For a personal single-account setup this lets tools be called without
    passing a connection id every time.
    """
    return _env(f"NANGO_CONN_{platform.upper()}")


settings = Settings()
