"""Per-platform metadata for the connection wizard.

Values verified against the live Nango provider catalog and current provider
consoles (2026-07). Keep the callback URL and scopes here — the wizard and the
setup guide both read from this single source so they never drift.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import settings


def callback_url() -> str:
    """The exact redirect/callback URL to register in the OAuth app.
    A single-character mismatch causes redirect_uri_mismatch, so this is THE
    value the user must copy verbatim."""
    return f"{settings.nango_host.rstrip('/')}/oauth/callback"


@dataclass(frozen=True)
class Platform:
    key: str
    label: str
    kind: str                       # "oauth" | "oauth_generic" | "browser"
    provider: str = ""              # Nango provider slug (verified present in catalog)
    scopes: list[str] = field(default_factory=list)
    console_label: str = ""
    console_url: str = ""
    difficulty: str = ""
    needs_review: bool = False      # platform requires an app-review step (Meta)
    # generic OAuth2 (no ready Nango provider, e.g. VK)
    authorization_url: str = ""
    token_url: str = ""
    notes: str = ""


PLATFORMS: dict[str, Platform] = {
    "youtube": Platform(
        key="youtube",
        label="YouTube",
        kind="oauth",
        provider="youtube",
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        console_label="Google Cloud Console",
        console_url="https://console.cloud.google.com/auth/clients/create",
        difficulty="лёгкая (начни с неё)",
        notes="Пока приложение в режиме «Testing», логиниться могут только "
        "добавленные тобой тест-пользователи — этого хватает для себя и друзей.",
    ),
    "instagram": Platform(
        key="instagram",
        label="Instagram",
        kind="oauth",
        provider="instagram",
        scopes=["instagram_business_basic", "instagram_business_content_publish"],
        console_label="Meta for Developers",
        console_url="https://developers.facebook.com/apps/",
        difficulty="средняя (нужен бизнес-аккаунт и ревью Meta)",
        needs_review=True,
        notes="Нужен Instagram-аккаунт типа «Бизнес», привязанный к странице Facebook. "
        "Публикация постов требует прохождения App Review в Meta — это не мгновенно.",
    ),
    "vk": Platform(
        key="vk",
        label="ВКонтакте",
        kind="oauth_generic",
        provider="vk",
        scopes=["wall", "offline"],
        console_label="VK ID / dev.vk.com",
        console_url="https://id.vk.com/about/business/go",
        difficulty="средняя (готового провайдера в Nango нет — generic OAuth2)",
        authorization_url="https://id.vk.com/authorize",
        token_url="https://id.vk.com/oauth2/auth",
        notes="В каталоге Nango нет готового провайдера VK, поэтому заводится как "
        "generic OAuth2 с адресами VK ID. Мастер подставит их автоматически.",
    ),
    "dzen": Platform(
        key="dzen",
        label="Яндекс Дзен",
        kind="browser",
        difficulty="особая (у Дзена нет API — вход через браузер)",
        notes="У Дзена нет OAuth/API для статей. Подключение — разовый ручной вход "
        "в браузере, сохраняется сессия (cookies), не токен. Отдельно от Nango.",
    ),
}


def get(key: str) -> Platform | None:
    return PLATFORMS.get(key)
