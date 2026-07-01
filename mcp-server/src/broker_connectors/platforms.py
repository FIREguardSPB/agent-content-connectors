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
    # concise, current, user-facing steps to create the OAuth app. Rendered
    # inline in the wizard AND read aloud step-by-step by the agent — the user
    # never has to open a file.
    steps: list[str] = field(default_factory=list)


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
        steps=[
            "Открой console.cloud.google.com и войди своим Google-аккаунтом.",
            "Вверху слева нажми список проектов → «New Project» → впиши имя → «Create». Убедись, что новый проект выбран.",
            "В строке поиска вверху набери «YouTube Data API v3» → открой → нажми «Enable».",
            "Слева: APIs & Services → OAuth consent screen (новый экран «Google Auth Platform») → «Get started»: имя приложения + твоя почта; тип — «External»; контактная почта; согласись → «Create».",
            "Там же → раздел «Audience» → «Test users» → «Add users» → впиши свой Gmail → «Save».",
            "Слева «Clients» → «Create client» → тип «Web application».",
            "В поле «Authorized redirect URIs» → «Add URI» → вставь адрес возврата (кнопка «Копировать» выше) → «Create».",
            "Появятся Client ID и Client secret — скопируй оба сюда, в поля ниже.",
        ],
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
        steps=[
            "Открой developers.facebook.com/apps → «Create App» → тип «Business».",
            "В приложении добавь продукт «Instagram» (Graph API) и «Facebook Login».",
            "В настройках входа найди «Valid OAuth Redirect URIs» → вставь адрес возврата (кнопка «Копировать» выше).",
            "Заяви права instagram_business_basic и instagram_business_content_publish и отправь на App Review (это не мгновенно).",
            "Возьми «App ID» (это Client ID) и «App Secret» (это Client Secret) → вставь сюда, в поля ниже.",
        ],
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
        steps=[
            "Открой dev.vk.com (или id.vk.com/about/business/go) → создай приложение типа «Веб»/«Сайт».",
            "В настройках укажи Redirect URI → вставь адрес возврата (кнопка «Копировать» выше).",
            "Включи права: wall (посты на стену) и offline (долгий доступ).",
            "Возьми «ID приложения» (Client ID) и «Защищённый ключ» (Client Secret) → вставь сюда, в поля ниже.",
        ],
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
