"""Process-wide NangoClient holder so tools stay simple and tests can inject."""
from __future__ import annotations

from .nango_client import NangoClient

_client: NangoClient | None = None


def set_client(client: NangoClient | None) -> None:
    global _client
    _client = client


def get_client() -> NangoClient:
    global _client
    if _client is None:
        _client = NangoClient()
    return _client
