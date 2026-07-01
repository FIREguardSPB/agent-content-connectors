"""Safely read/update mcp-server/.env so the wizard can persist connection ids
without the user ever editing a file."""
from __future__ import annotations

from pathlib import Path

DEFAULT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def set_var(key: str, value: str, path: Path | None = None) -> Path:
    """Set key=value in the .env file, updating in place or appending. Idempotent."""
    p = path or DEFAULT_ENV_PATH
    lines = p.read_text().splitlines() if p.exists() else []
    out: list[str] = []
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped.split("=", 1)[0].strip() == key:
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    p.write_text("\n".join(out) + "\n")
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return p


def get_var(key: str, path: Path | None = None) -> str | None:
    p = path or DEFAULT_ENV_PATH
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            if k.strip() == key:
                return v.strip()
    return None
